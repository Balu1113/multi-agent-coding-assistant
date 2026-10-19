import pytest
from src.code_gen import generate_code


def test_stock_max_profit():
    code = generate_code("maximize profit from a single buy-sell transaction")
    assert "def max_profit" in code
    assert "prices" in code
    assert "min_price" in code
    assert "max_profit" in code


def test_fibonacci():
    code = generate_code("fibonacci sequence")
    assert "def fibonacci" in code


def test_binary_search():
    code = generate_code("binary search")
    assert "def binary_search" in code


def test_quicksort():
    code = generate_code("quicksort algorithm")
    assert "def quicksort" in code


def test_fizzbuzz():
    code = generate_code("fizzbuzz")
    assert "def fizzbuzz" in code


def test_two_sum():
    code = generate_code("two sum problem")
    assert "def two_sum" in code


def test_palindrome():
    code = generate_code("palindrome check")
    assert "def is_palindrome" in code


def test_reverse_linked_list():
    code = generate_code("reverse linked list")
    assert "def reverse_list" in code


def test_tree_traversal():
    code = generate_code("binary tree traversal")
    assert "def inorder_traversal" in code


def test_factorial():
    code = generate_code("factorial")
    assert "def factorial" in code


def test_is_prime():
    code = generate_code("prime number check")
    assert "def is_prime" in code


def test_unknown_prompt():
    code = generate_code("do something completely random and unknown")
    assert "def solve" in code or "raise NotImplementedError" in code


def test_container_with_most_water():
    code = generate_code("container with most water")
    assert "def max_area" in code
    assert "def max_area_two_pointer" in code
    assert "def max_area_bruteforce" in code
    assert "height" in code


def test_container_alternate_prompts():
    for p in ["max area of water", "largest container", "most water container"]:
        code = generate_code(p)
        assert "def max_area" in code, f"Failed for prompt: {p}"

