"""Функциональный синтаксический анализ"""
import re

class Constituent:
    """Класс-контейнер для составляющих, содержит три атрибута:
    - tag: метка категории (или None)
    - children: дочерние составляющие
    - words: линейный список слов составляющей"""

    def __init__(self, tag=None, children=(), words=()):
        self.tag = tag
        self.children = children
        self.words = words
        
    def __add__(self, other):
        """Конкатенация для составляющих (поддержка оператора +)"""

        return Constituent(children=(self, other),
                           words=self.words + other.words)

    def __matmul__(self, tag):
        """Добавление метки к составляющей (поддержка оператора @)"""

        return Constituent(tag=tag, children=self.children, words=self.words)

    def __str__(self):
        """Строковое представление составляющей (поддержка str(c))"""

        if self.children:
            arguments = ','.join([ str(child) for child in self.children])
        else:
            arguments = ','.join(self.words)

        return f"{self.tag if self.tag is not None else ''}({arguments})"
    
    def __eq__(self, other):
        """Сравнивает две составляющие по содержимому, а не по уникальным идентификаторам."""
        if isinstance(other, Constituent):
            return self.tag == other.tag and self.children == other.children and self.words == other.words
        return False

    def __ne__(self, other):
        """Определяет неравенство двух составляющих."""
        return not self.__eq__(other)
    def __repr__(self):
        return f"Constituent(tag={self.tag}, children={self.children}, words={self.words})"

class Parser:
    """Базовый класс парсеров, реализует только поддержку операторов"""

    def __add__(self, other):
        """Конкатенация парсеров (поддержка оператора +)"""
        return SeqParser(self, other)

    def __or__(self, other):
        """Альтерация парсеров (поддержка оператора |)"""
        return AltParser(self, other)

    def __matmul__(self, tag):
        """Добавление категориальной метки (поддержка оператора @)"""
        return TagParser(tag, self)

    def __call__(self, tokens):
        """Все подклассы должны переопределить этот метод так, чтобы
        он возвращал генератор (yield), выдающий пары (составляющая, хвост цепочки)"""
        pass
        
class WordParser(Parser):
    """Парсер, который принимает ровно одно заданное слово"""

    def __init__(self, w):
        self.w = w

    def __call__(self, tokens):
        """Генератор порождает не более одной пары, где в составляющей тег пустой,
        детей нет, а список слов состоит из одного слова"""
        if len(tokens) > 0 and tokens[0] == self.w:
            yield (Constituent(words=(self.w,)), tokens[1:])


class SeqParser(Parser):
    """Парсер --- конкатенация парсеров"""

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def __call__(self, tokens):
        """Сначала вызывается парсер p1, потом для каждого возможного хвоста
        вызывается парсер p2. Результирующая составляющая есть конкатенация
        составляющих с пустым тегом"""
        for c1, tokens1 in self.p1(tokens):
            for c2, tokens2 in self.p2(tokens1):
                yield (c1 + c2, tokens2)

class AltParser(Parser):
    """Парсер --- альтерация парсеров"""

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def __call__(self, tokens):
        """Возвращаются последовательно варианты разбора от обоих парсеров"""
        yield from self.p1(tokens)
        yield from self.p2(tokens)

class TagParser(Parser):
    """Парсер, снабжающий меткой результат нижележащего парсера"""

    def __init__(self, tag, p):
        self.p = p
        self.tag = tag

    def __call__(self, tokens):
        """Метки составляющих заменяются на tag"""
        for c, tokens1 in self.p(tokens):
            yield (c @ self.tag, tokens1)


class FilterParser(Parser):
    """Базовый парсер-фильтр"""

    def __init__(self, p):
        self.p = p

    def predicate(self, c):
        """Метод должен быть переопределен в подклассах,
        чтобы определять валидность составляющей c"""
        return True

    def __call__(self, tokens):
        """Возвращаются только те результаты нижележащего
        парсера, составляющая которых удовлетворяет методу predicate"""
        for c, tokens1 in self.p(tokens):
            if self.predicate(c):
                yield (c, tokens1)

class RecursiveParser(Parser):
    """Парсер --- рекурсивное замыкание.

    Например:
       RecursiveParser(lambda self: N | Adj + self)
    вызывает N или Adj, а затем рекурсивно самого себя.

    Внимание: рекурсивный аргумент не может быть самым
    левым аргументом + и т.п.
    """

    def __init__(self, fp):
        self.p = fp(self)

    def __call__(self, tokens):
        """Вызывает рекурсивно замкнутый нижележащий парсер"""
        yield from self.p(tokens)


class WholeParser(Parser):
    """Парсер законченных выражений"""

    def __init__(self, p):
        self.p = p

    def __call__(self, tokens):
        """Возвращает только те результаты нижележащего парсера,
        у который хвост --- пустая цепочка"""
        for c, tokens1 in self.p(tokens):
            if not tokens1:
                yield (c, tokens1)

def word(w):
    """Сокращение для конструктора WordParser"""
    return WordParser(w)

def recursive(fp):
    """Сокращение для конструктора RecursiveParser"""
    return RecursiveParser(fp)

def whole(p):
    """Сокращение для конструктора WholeParser"""
    return WholeParser(p)


N = (word('fox') | word('wolf') | word('ant') | word('table')) @ 'N'
Adj = (word('quick') | word('brown') | word('table') | word('caught') |
       word('adorable')) @ 'Adj'
Compl = (word('a') | word('an') | word('the')) @ 'Compl'
V = (word('jump') | word('jumped') | word('caught')) @ 'V'

class FilterValidArticle(FilterParser):
    """Подкласс FilterParser, который обеспечивает выбор корректного артикля"""

    def predicate(self, c):
        """Предикат будет истинен:
        - если у составляющей нет детей или первый ребенок --- не артикль
        - если первое слово "a", а второе слово не начинается с гласной
        - если первое слово "an", а второе слово начинается с гласной
        - если первое слово --- другой артикль ("the")
        """
        if not c.children or c.children[0].tag != 'Compl':
            return True

        if c.words[0] == 'a':
            return re.match('[^aeiou]', c.words[1])
        if c.words[0] == 'an':
            return re.match('[aeiou]', c.words[1])
        return True

NP0 = recursive(lambda NP0: (N | Adj + NP0) @ 'NP')
NP = FilterValidArticle(Compl + NP0) @ 'NP'

VP = V @ 'VP'

S = (NP + VP) @ 'S'


class StarParser:
    """Парсер-звездочка, вызывает нижележащий парсер ноль или более раз"""
    def __init__(self, p):
        self.p = p

    def __call__(self, tokens):
        children = []
        while tokens:
            result = None # возвращает пустую составляющую
            for res in self.p(tokens):
                result = res
                break  # выходим из цикла, так как нам нужен только первый результат

            if result is None or result[0] is None:
                break

            (tree, remainder) = result # сохраняем результат и его "хвост"
            children.append(tree)
            tokens = remainder # перезаписываем остаточные токены в виде "хвоста"

        yield Constituent(children=tuple(children), words=tuple(word for child in children for word in child.words)), tokens



def star(p):
    """Сокращение для конструктора StarParser"""
    return StarParser(p)


def test_star_parser():
    p1 = star(word('a'))
    result1 = list(p1(['a', 'b']))[0]
    expected1 = (
        Constituent(children=(
            Constituent(words=('a',), children=()),)
        , words=('a',)),
        ['b']
    )
    assert result1 == expected1, f"Expected {expected1}, but got {result1}"
    print(f"Test passed for result1: {result1}")
    
    p2 = star(word('a') | word('b'))
    result2 = list(p2(['a', 'b', 'c']))[0]
    expected2 = (
        Constituent(children=(
            Constituent(words=('a',), children=()),
            Constituent(words=('b',), children=()))
        , words=('a', 'b')),
        ['c']
    )
    assert result2 == expected2, f"Expected {expected2}, but got {result2}"
    print(f"Test passed for result2: {result2}")
    
    
    p3 = star(word('a') | word('b'))
    result3 = list(p3(['a', 'b', 'b']))[0]
    expected3 = (
        Constituent(children=(
            Constituent(words=('a',), children=()),
            Constituent(words=('b',), children=()),
            Constituent(words=('b',), children=()))
        , words=('a', 'b', 'b')),
        []
    )
    assert result3 == expected3, f"Expected {expected3}, but got {result3}"
    print(f"Test passed for result3: {result3}")
    
    
    p4 = star(word('a') | word('b'))
    result4 = list(p4(['c']))[0]
    expected4 = (
        Constituent(children=(), words=()),
        ['c']
    )
    assert result4 == expected4, f"Expected {expected4}, but got {result4}"
    print(f"Test passed for result4: {result4}")
    
    
test_star_parser()