import itertools
import random
import time
from typing import List

import helpers

from copy import deepcopy
from mpi4py import MPI

from Board import Board, Mover
from helpers import Message, EVENT

comm = MPI.COMM_WORLD
RANK = comm.Get_rank()
SIZE = comm.Get_size()
MASTER_PID = 0
DEPTH = 6

BOARD = Board()


def generate_tasks():
    base = [list(range(1, BOARD.total_columns + 1))] * DEPTH
    return list(itertools.product(*base))


def CPU_move():
    depth = DEPTH
    best = -1
    best_col = 0

    board = deepcopy(BOARD)  # make copy of original board to simulate plays
    message = Message(EVENT.SEND_BOARD, board)
    comm.bcast(message.to_dict(), root=MASTER_PID)

    tasks = generate_tasks()

    while len(tasks):
        status = MPI.Status()
        data = comm.recv(source=MPI.ANY_SOURCE, status=status)
        message = Message.from_dict(data)
        from_pid = status.Get_source()

        if message.type == EVENT.SEND_TASK:
            send_task_msg = Message(EVENT.SEND_TASK, tasks.pop())
            helpers.send_msg_to_worker(send_task_msg, from_pid)

        if message.type == EVENT.SEND_RESULT:
            # recievo si rezultat
            result = message.payload[0]
            if result > best or (result == best and random.random() > 0.5):
                best = result
                best_col = message.payload[1]
        # time.sleep(1)
    for pid in range(1, SIZE): helpers.send_msg_to_worker(Message(EVENT.BOARD_COMPLETE), pid)
    return best_col


def master_process():
    # setup board and screen
    BOARD.load()
    BOARD.render()

    while True:
        column = int(input("Select column: "))
        print('Last move --> ', column, ' \n')

        if not BOARD.is_move_legal(column):
            BOARD.render('Illegal move')
            continue

        BOARD.move(column, Mover.PLAYER)  # move player
        # BOARD.render()
        BOARD.move(CPU_move(), Mover.CPU)  # move CPU
        BOARD.render()

        if BOARD.is_game_over():
            print('Game is over!')
            break


def worker_process():
    while True:
        data = comm.bcast(None, root=0)
        message = Message.from_dict(data)
        print(message.type, RANK, flush=True)

        if message.type == EVENT.SEND_BOARD:
            # get board copy from payload
            board: Board = message.payload
            while True:
                # send request for task
                helpers.send_msg_to_master(Message(EVENT.SEND_TASK))
                # receive task
                m = helpers.recv_msg(MASTER_PID)
                if m.type == EVENT.BOARD_COMPLETE:
                    break
                tasks = m.payload

                for i, move in enumerate(tasks):
                    mover = Mover.CPU if i % 2 == 0 else Mover.PLAYER
                    if board.is_move_legal(move):
                        board.move(move, mover)

                if board.is_game_over():
                    helpers.send_msg_to_master(Message(EVENT.SEND_RESULT, (-1, tasks[0])))

                result = board.evaluate(Mover.CPU, DEPTH - len(tasks))
                helpers.send_msg_to_master(Message(EVENT.SEND_RESULT, (result, tasks[0])))

                for i in range(len(tasks)-1): board.undo_move()  # clean moves

        time.sleep(1)


def main():
    if RANK == MASTER_PID:
        master_process()
    else:
        worker_process()


if __name__ == '__main__':
    # comm.barrier()
    main()
    MPI.Finalize()
