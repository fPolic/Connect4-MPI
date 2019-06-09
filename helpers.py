import itertools
import operator
import os
import random
from functools import reduce

from mpi4py import MPI

comm = MPI.COMM_WORLD


class EVENT:
    SEND_BOARD = 'EVENT_SEND_BOARD'
    SEND_TASK = 'EVENT_SEND_TASK'
    SEND_RESULT = 'EVENT_SEND_RESULT'
    BOARD_COMPLETE = 'EVENT_BOARD_COMPLETE'


class Message:
    type: str
    payload: object

    def __init__(self, type: str, payload: object = None):
        self.type = type
        self.payload = payload

    def to_dict(self):
        return {'type': self.type, 'payload': self.payload}

    @classmethod
    def request_work_message(cls, payload: object):
        # factory for messages
        return cls(EVENT.REQUEST_WORK, payload)

    @classmethod
    def from_dict(cls, dict: dict):
        return cls(dict['type'], dict['payload'])


def generate_tasks(total_columns: int, depth: int):
    base = [list(range(1, total_columns + 1))] * depth
    tasks = list(itertools.product(*base))
    # random.shuffle(tasks)
    return tasks


def send_msg_to_worker(msg: str or object, worker_id: int) -> None:
    if isinstance(msg, Message):
        comm.send(msg.to_dict(), dest=worker_id)
    else:
        comm.send(msg, dest=worker_id)


def send_msg_to_master(msg: str or object) -> None:
    send_msg_to_worker(msg, 0)


def recv_msg(source=0) -> Message:
    data = comm.recv(source=source)
    return Message.from_dict(data)


def calculate_best_move(results) -> int:
    best_col = 0
    best_result = -1

    for column, values in results.items():
        res = reduce(operator.add, values) / len(values)
        if res > best_result or (res == best_result and random.random() > 0.5):
            best_result = res
            best_col = column
            print(best_col, str(best_result), flush=True)

    return best_col


def clear_screen(): return os.system('clear')
