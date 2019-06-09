from typing import List

import helpers


class Mover:
    PLAYER = '1'
    CPU = '2'


class Winner:
    PLAYER = -1
    CPU = 1


class Board:
    __state: List[List[str]]
    total_columns: int
    total_rows: int
    moves_stack: List[List[int]]

    Mover: Mover
    Winner: Winner

    def __init__(self):
        self.__state = list()
        self.total_columns = -1
        self.total_rows = -1
        self.moves_stack = list()

    def __str__(self):
        separator_length: int = round(self.total_columns * 2.2)
        header: str = '\033[95m' + '| ' + ' | '.join(
            map(str, range(1, self.total_columns + 1))) + ' |\n' + '\033[0m'
        ret: str = '- ' * separator_length + '\n'

        for row in self.__state:
            ret += '| ' + ' | '.join(row) + ' |\n'
            ret += '- ' * separator_length + '\n'
        ret = ret.replace('1', 'X')
        ret = ret.replace('2', 'O')
        ret = ret.replace('0', ' ')

        return header + ret

    def load(self):
        lines = open('ploca.txt', 'r').readlines()
        size = lines[0].strip().split(' ')
        self.total_rows = int(size[0])
        self.total_columns = int(size[1])

        for line in lines[1:]:
            row = line.strip().split('  ')
            self.__state.append(row)

    def render(self, msg: str = ''):
        helpers.clear_screen()
        print(self, flush=True)
        if msg != '':
            print(msg, flush=True)

    def move(self, column: int, mover: Mover):
        index = self.total_rows - 1  # add to bottom row
        for i, r in enumerate(self.__state):
            if r[column - 1] != '0':
                index = i - 1
                break
        self.__state[index][column - 1] = mover
        self.moves_stack.append([index, column - 1])

    def undo_move(self):
        # unset last element of array
        last_move = self.moves_stack.pop()
        self.__state[last_move[0]][last_move[1]] = '0'

    def is_game_over(self):
        # check horizontals
        for s in self.__state:
            row = ''.join(s)
            if row.find('1111') + row.find('2222') > -2:
                return True

        # negative diagonal
        for i in range(self.total_rows - 3):
            for j in range(self.total_columns - 3):
                base = self.__state[i][j]
                match_count = 0
                for k in range(4):
                    if self.__state[i + k][j + k] == base and base != '0':
                        match_count += 1
                if match_count == 4:
                    return True

        # positive diagonal
        for i in range(self.total_rows - 3):
            for j in range(3, self.total_columns - 1):
                base = self.__state[i][j]
                match_count = 0
                for k in range(4):
                    if self.__state[i + k][j - k] == base and base != '0':
                        match_count += 1
                if match_count == 4:
                    return True

        return False

    def is_move_legal(self, column: int):
        # move is not legal if top row
        # `column` is already taken
        if self.__state[0][column - 1] != '0' or column > self.total_columns:
            return False
        return True

    def evaluate(self, mover: Mover, depth: int) -> float:
        all_loose = True
        all_winn = True
        num_moves = 0
        total = 0.0

        if self.is_game_over(): return Winner.CPU if mover == Mover.CPU else Winner.PLAYER
        if depth == 0: return 0

        depth = depth - 1
        new_mover = Mover.PLAYER if mover == Mover.CPU else Mover.CPU

        for column in range(1, 8):
            if not self.is_move_legal(column): continue
            num_moves += 1

            self.move(column, new_mover)
            result = self.evaluate(new_mover, depth)
            self.undo_move()

            if result > -1: all_loose = False
            if result != 1: all_winn = False

            if result == 1 and new_mover == Mover.CPU: return Winner.CPU
            if result == -1 and new_mover == Mover.PLAYER: return Winner.PLAYER

            total = total + result

        if all_winn: return Winner.CPU
        if all_loose: return Winner.PLAYER
        return total / num_moves
