import itertools
import operator
import random
import time
from functools import reduce
from typing import List

import helpers

from copy import deepcopy
from mpi4py import MPI

from Board import Board, Mover, Winner
from helpers import Message, EVENT

comm = MPI.COMM_WORLD
RANK = comm.Get_rank()
SIZE = comm.Get_size()
MASTER_PID = 0
DEPTH = 5

BOARD = Board()


def CPU_move():
    board = deepcopy(BOARD)  # make copy of original board to simulate plays
    message = Message(EVENT.SEND_BOARD, board)
    comm.bcast(message.to_dict(), root=MASTER_PID)

    tasks = helpers.generate_tasks(BOARD.total_columns, DEPTH)
    results = dict()
    for i in range(1, BOARD.total_columns + 1):
        results[i] = list()

    while len(tasks):
        status = MPI.Status()
        # wait on message from any worker
        data = comm.recv(source=MPI.ANY_SOURCE, status=status)
        # parse message
        message = Message.from_dict(data)
        # get ready worker ID
        from_pid = status.Get_source()

        if message.type == EVENT.SEND_TASK:
            # if message was request for task
            send_task_msg = Message(EVENT.SEND_TASK, tasks.pop())
            # send that worker next task
            helpers.send_msg_to_worker(send_task_msg, from_pid)

        if message.type == EVENT.SEND_RESULT:
            data = message.payload  # [result, column]
            results[data[1]].append(data[1])

    message_board_complete = Message(EVENT.BOARD_COMPLETE)
    for pid in range(1, SIZE): helpers.send_msg_to_worker(message_board_complete, pid)

    return helpers.calculate_best_move(results)


def game_over(mover: Mover):
    mvr = 'CPU' if mover == Mover.CPU else 'PLAYER'
    print('GAME OVER, ' + mvr + ' WINN!!!', flush=True)

    MPI.Finalize()
    exit(0)


def master_process():
    # setup board and screen
    BOARD.load()
    BOARD.render()

    while True:
        column = int(input("Select column: "))

        if not BOARD.is_move_legal(column):
            BOARD.render('Illegal move')
            continue

        BOARD.move(column, Mover.PLAYER, log=True)  # move player
        BOARD.render()
        if BOARD.is_game_over(): game_over(Mover.PLAYER)

        print('CPU is thinking...', flush=True)

        BOARD.move(CPU_move(), Mover.CPU, log=True)  # move CPU
        BOARD.render()
        if BOARD.is_game_over(): game_over(Mover.CPU)


def worker_process():
    while True:
        data = comm.bcast(None, root=0)
        board_message = Message.from_dict(data)

        if board_message.type == EVENT.SEND_BOARD:
            # get board copy from payload
            board: Board = board_message.payload
            while True:
                # send request for task
                helpers.send_msg_to_master(Message(EVENT.SEND_TASK))
                # receive task
                task_message = helpers.recv_msg(MASTER_PID)
                # if current move is calculated, go request new board
                if task_message.type == EVENT.BOARD_COMPLETE:
                    break

                moves_made = 0
                last_mover = Mover.CPU
                tasks = task_message.payload
                for i, move in enumerate(tasks):
                    # play moves from task and check if move leeds to game over
                    mover = Mover.CPU if i % 2 == 0 else Mover.PLAYER
                    if board.is_move_legal(move):
                        board.move(move, mover)
                        moves_made += 1
                        last_mover = mover
                        if board.is_game_over():
                            send_result = Winner.CPU if mover == Mover.CPU else Winner.PLAYER
                            helpers.send_msg_to_master(Message(EVENT.SEND_RESULT, (send_result, tasks[0])))
                            break

                result = board.evaluate(last_mover, DEPTH - len(tasks))
                print('work ', RANK, ' --> ', result)
                helpers.send_msg_to_master(Message(EVENT.SEND_RESULT, (result, tasks[0])))

                for _ in range(moves_made): board.undo_move()  # clean moves

        time.sleep(1)  # only while waiting for board


def main():
    if RANK == MASTER_PID:
        master_process()
    else:
        worker_process()


if __name__ == '__main__':
    comm.barrier()
    main()
