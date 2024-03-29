DIGITS = '0123456789'
TT_INT = 'INT'
TT_FLOAT = 'FLOAT'
TT_MINUS = 'MINUS'
TT_POW = 'POW'
TT_PLUS = 'PLUS'
TT_MUL = 'MUL'
TT_DIV = 'DIV'
TT_LPAREN = 'LPAREN'
TT_RPAREN = 'RPAREN'
TT_EOF = 'EOF'


class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result = f'{self.error_name} : {self.details}'
        result += f'\n File {self.pos_start.fn} : Line {self.pos_end.ln + 1}'
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=''):
        super().__init__(pos_start, pos_end, 'Invalid Syntax Error', details)


class RuntimeError(Error):
    def __init__(self, pos_start, pos_end, details=''):
        super().__init__(pos_start, pos_end, 'Runtime Error', details)


class Position:
    def __init__(self, idx, ln, col, fn, ftxt):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.fn = fn
        self.ftxt = ftxt
        self.prev = None

    def advance(self, current_char = None):
        self.prev = self.copy()
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0
        return self

    def back(self):
        return self.prev

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.fn, self.ftxt)


class Token:
    def __init__(self, _type, value=None, pos_start=None, pos_end=None):
        self.type = _type
        self.value = value

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = self.pos_start.copy()
            self.pos_end.advance()

        if pos_end:
            self.pos_end = pos_end

    def __repr__(self):
        if self.value:
            return f'{self.type} : {self.value}'
        return f'{self.type}'


class Lexer:
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.position = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.position.advance(self.current_char)
        self.current_char = self.text[self.position.idx] if self.position.idx < len(self.text) else None

    def back(self):
        # print(vars(self.position))
        self.position = self.position.back()
        # print(vars(self.position))
        self.current_char = self.text[self.position.idx] if self.position.idx >= 0 else None

    def make_tokens(self):
        tokens = []
        while self.current_char is not None:
            if self.current_char not in ' \t':
                if self.current_char == '+':
                    tokens.append(Token(TT_PLUS, pos_start=self.position))
                elif self.current_char == '-':
                    tokens.append(Token(TT_MINUS, pos_start=self.position))
                elif self.current_char == '*':
                    tokens.append(Token(TT_MUL, pos_start=self.position))
                elif self.current_char == '/':
                    tokens.append(Token(TT_DIV, pos_start=self.position))
                elif self.current_char == '(':
                    tokens.append(Token(TT_LPAREN, pos_start=self.position))
                elif self.current_char == ')':
                    tokens.append(Token(TT_RPAREN, pos_start=self.position))
                elif self.current_char == '^':
                    tokens.append(Token(TT_POW, pos_start=self.position))
                elif self.current_char in DIGITS:
                    tokens.append(self.make_number())
                    self.back()
                else:
                    pos_start = self.position.copy()
                    char = self.current_char
                    self.advance()
                    return [], IllegalCharError(pos_start, self.position, "'" + char + "'")
            self.advance()
        tokens.append(Token(TT_EOF, pos_start=self.position))
        return tokens, None

    def make_number(self):
        num_str = ''
        dot_count = 0
        pos_start = self.position.copy()
        while self.current_char is not None and self.current_char in DIGITS + '.':
            if self.current_char == '.':
                dot_count += 1
            num_str += self.current_char
            self.advance()
        if dot_count > 0:
            return Token(TT_FLOAT, float(num_str), pos_start, self.position)
        return Token(TT_INT, int(num_str), pos_start, self.position)


class NumberNode:
    def __init__(self, tok):
        self.tok = tok

    def __repr__(self):
        return f'{self.tok}'


class BinOpNode:
    def __init__(self, left_node, op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node

    def __repr__(self):
        return f'({self.left_node}, {self.op_tok}, {self.right_node})'


class UnaryOpNode:
    def __init__(self, op_tok, node):
        self.op_tok = op_tok
        self.node = node

    def __repr__(self):
        return f"({self.op_tok}, {self.node})"



class ParseResults:
    def __init__(self):
        self.error = None
        self.node = None

    def register(self, res):
        if isinstance(res, ParseResults):
            if res.error: self.error = res.error
            return res.node
        return res

    def success(self, node):
        self.node = node
        return self
    def failure(self, error):
        self.error = error
        return self


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.current_tok = None
        self.advance()

    def advance(self):
        self.tok_idx += 1
        self.current_tok = self.tokens[self.tok_idx] if self.tok_idx < len(self.tokens) else None
        return self.current_tok

    def parse(self):
        res = self.expr()
        if not res.error and self.current_tok.type != TT_EOF :
            return res.failure(InvalidSyntaxError(self.current_tok.pos_start, self.current_tok.pos_end, "Expected '+' '-' '*' '/' "))
        return res

    def expr(self):
        return self.bin_op(self.term, (TT_MINUS, TT_PLUS))

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV))

    def bin_op(self, func, ops):
        res = ParseResults()
        left = res.register(func())
        if res.error:
            return res
        while self.current_tok.type in ops:
            op_tok = self.current_tok
            res.register(self.advance())
            right = res.register(func())
            if res.error:
                return res
            left = BinOpNode(left, op_tok, right)
        return res.success(left)

    def factor(self):
        res = ParseResults()
        tok = self.current_tok

        if tok.type in (TT_PLUS, TT_MINUS):
            res.register(self.advance())
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))
        elif tok.type in (TT_INT, TT_FLOAT):
            res.register(self.advance())
            return res.success(NumberNode(tok))
        elif tok.type == TT_LPAREN:
            res.register(self.advance())
            expr = res.register(self.expr())
            if res.error:
                return res
            if self.current_tok.type == TT_RPAREN:
                res.register(self.advance())
                return res.success(expr)
            else:
                return res.failure(InvalidSyntaxError(self.current_tok.pos_start, self.current_tok.pos_end, "Expected ')' "))
        return res.failure(InvalidSyntaxError(tok.pos_start, tok.pos_end, "Expected int or Float"))

def run(fn, text):
    # Generate tokens
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    # Generate Abstract Syntax Tree
    parser = Parser(tokens)
    ast = parser.parse()
    # interpreter = Interpreter()
    # interpreter.visit(ast.node)
    return ast.node, ast.error
