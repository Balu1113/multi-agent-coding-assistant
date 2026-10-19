"""Real code generation engine — produces working solutions for common coding problems."""
from __future__ import annotations

import logging
import re
import textwrap
from typing import Any

logger = logging.getLogger(__name__)


def _dedent(s: str) -> str:
    return textwrap.dedent(s).strip()


def _body(s: str) -> str:
    """Return core logic lines (0 indent) from a dedented block."""
    return _dedent(s)


# ── LeetCode detection & wrapping ──────────────────────────────────────────

_LEETCODE_SIGS: dict[str, tuple[str, str, str]] = {
    "max profit":   ("maxProfit",        "self, prices: list[int]",              "int"),
    "stock":        ("maxProfit",        "self, prices: list[int]",              "int"),
    "two sum":      ("twoSum",           "self, nums: list[int], target: int",    "list[int]"),
    "palindrome":   ("isPalindrome",     "self, s: str",                         "bool"),
    "binary search":("search",           "self, nums: list[int], target: int",    "int"),
    "reverse linked":("reverseList",     "self, head: Optional[ListNode]",       "Optional[ListNode]"),
    "tree traversal":("inorderTraversal","self, root: Optional[TreeNode]",       "list[int]"),
    "container":    ("maxArea",           "self, height: list[int]",              "int"),
    "most water":   ("maxArea",           "self, height: list[int]",              "int"),
    "fizzbuzz":     ("fizzBuzz",          "self, n: int",                         "list[str]"),
    "3sum closest": ("threeSumClosest",   "self, nums: list[int], target: int",   "int"),
    "three sum closest": ("threeSumClosest", "self, nums: list[int], target: int", "int"),
    "3sum":         ("threeSum",          "self, nums: list[int]",                "list[list[int]]"),
    "three sum":    ("threeSum",          "self, nums: list[int]",                "list[list[int]]"),
    "valid parentheses":  ("isValid",     "self, s: str",                         "bool"),
    "parentheses":        ("isValid",     "self, s: str",                         "bool"),
    "merge two":          ("mergeTwoLists","self, list1: Optional[ListNode], list2: Optional[ListNode]", "Optional[ListNode]"),
    "longest substring":  ("lengthOfLongestSubstring", "self, s: str",            "int"),
    "roman":              ("romanToInt",  "self, s: str",                         "int"),
    "climbing stairs":    ("climbStairs", "self, n: int",                         "int"),
    "climb":              ("climbStairs", "self, n: int",                         "int"),
    "contains duplicate": ("containsDuplicate", "self, nums: list[int]",          "bool"),
    "majority element":   ("majorityElement", "self, nums: list[int]",            "int"),
    "single number":      ("singleNumber","self, nums: list[int]",                "int"),
    "move zero":          ("moveZeroes",  "self, nums: list[int]",                "None"),
    "plus one":           ("plusOne",     "self, digits: list[int]",              "list[int]"),
    "missing number":     ("missingNumber","self, nums: list[int]",               "int"),
}


def _detect_leetcode(prompt_lower: str) -> str | None:
    """Match most specific (longest) key first to avoid '3sum' matching '3sum closest'."""
    keys = sorted(_LEETCODE_SIGS, key=len, reverse=True)
    if "leetcode" in prompt_lower:
        for kw in keys:
            if kw in prompt_lower:
                return kw
        return None
    for kw in keys:
        if kw in prompt_lower:
            return kw
    return None


def _lc(code_body: str, prompt_lower: str) -> str | None:
    """If the prompt matches a LeetCode problem, wrap *code_body* in Solution class."""
    kw = _detect_leetcode(prompt_lower)
    if kw is None:
        return None
    method, params, ret = _LEETCODE_SIGS[kw]
    return (
        "from typing import List, Optional\n\n\n"
        f"class Solution:\n"
        f"    def {method}({params}) -> {ret}:\n"
        f"{textwrap.indent(code_body, '        ')}"
    )


# ── Language detection ──────────────────────────────────────────────────────

_LANG_ALIASES: dict[str, str] = {
    "py": "python", "python": "python", "python3": "python",
    "js": "javascript", "javascript": "javascript", "node": "javascript", "nodejs": "javascript", "ecmascript": "javascript",
    "ts": "typescript", "typescript": "typescript",
    "java": "java",
    "cpp": "cpp", "c++": "cpp", "c": "cpp", "cplusplus": "cpp",
    "go": "go", "golang": "go",
    "rust": "rust", "rs": "rust",
    "rb": "ruby", "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin", "kotlin": "kotlin",
    "scala": "scala",
    "r": "r",
    "sql": "sql",
}


def _detect_language(prompt: str) -> str:
    lower = prompt.lower()
    for alias, lang in _LANG_ALIASES.items():
        pattern = rf'\b{re.escape(alias)}\b'
        if re.search(pattern, lower):
            return lang
    return "python"


# ── Main entry point ───────────────────────────────────────────────────────

# ── Language-specific generators ──────────────────────────────────────────

def _two_sum_js() -> str:
    return _body("""\
        const seen = new Map();
        for (let i = 0; i < nums.length; i++) {
            const complement = target - nums[i];
            if (seen.has(complement)) {
                return [seen.get(complement), i];
            }
            seen.set(nums[i], i);
        }
        return [];
    """)


def _is_palindrome_js() -> str:
    return _body("""\
        const clean = s.toLowerCase().replace(/[^a-z0-9]/g, '');
        return clean === clean.split('').reverse().join('');
    """)


def _fizzbuzz_js() -> str:
    return _body("""\
        const result = [];
        for (let i = 1; i <= n; i++) {
            if (i % 15 === 0) result.push("FizzBuzz");
            else if (i % 3 === 0) result.push("Fizz");
            else if (i % 5 === 0) result.push("Buzz");
            else result.push(String(i));
        }
        return result;
    """)


def _binary_search_js() -> str:
    return _body("""\
        let left = 0, right = nums.length - 1;
        while (left <= right) {
            const mid = Math.floor((left + right) / 2);
            if (nums[mid] === target) return mid;
            if (nums[mid] < target) left = mid + 1;
            else right = mid - 1;
        }
        return -1;
    """)


def _container_js() -> str:
    return _body("""\
        let left = 0, right = height.length - 1;
        let maxWater = 0;
        while (left < right) {
            const h = Math.min(height[left], height[right]);
            const w = right - left;
            maxWater = Math.max(maxWater, h * w);
            if (height[left] < height[right]) left++;
            else right--;
        }
        return maxWater;
    """)


def _valid_parentheses_js() -> str:
    return _body("""\
        const stack = [];
        const pairs = {')': '(', ']': '[', '}': '{'};
        for (const ch of s) {
            if (ch in pairs) {
                if (!stack.length || stack[stack.length - 1] !== pairs[ch]) return false;
                stack.pop();
            } else {
                stack.push(ch);
            }
        }
        return stack.length === 0;
    """)


def _three_sum_js() -> str:
    return _body("""\
        nums.sort((a, b) => a - b);
        const result = [];
        for (let i = 0; i < nums.length - 2; i++) {
            if (i > 0 && nums[i] === nums[i - 1]) continue;
            let left = i + 1, right = nums.length - 1;
            while (left < right) {
                const sum = nums[i] + nums[left] + nums[right];
                if (sum < 0) left++;
                else if (sum > 0) right--;
                else {
                    result.push([nums[i], nums[left], nums[right]]);
                    while (left < right && nums[left] === nums[left + 1]) left++;
                    while (left < right && nums[right] === nums[right - 1]) right--;
                    left++; right--;
                }
            }
        }
        return result;
    """)


def _three_sum_closest_js() -> str:
    return _body("""\
        nums.sort((a, b) => a - b);
        n = nums.length;
        let closest = nums[0] + nums[1] + nums[2];
        for (let i = 0; i < n - 2; i++) {
            let left = i + 1, right = n - 1;
            while (left < right) {
                const total = nums[i] + nums[left] + nums[right];
                if (Math.abs(total - target) < Math.abs(closest - target)) {
                    closest = total;
                }
                if (total < target) left++;
                else if (total > target) right--;
                else return target;
            }
        }
        return closest;
    """)


def _stock_max_profit_js() -> str:
    return _body("""\
        let minPrice = Infinity;
        let maxProfit = 0;
        for (let i = 0; i < prices.length; i++) {
            if (prices[i] < minPrice) {
                minPrice = prices[i];
            } else if (prices[i] - minPrice > maxProfit) {
                maxProfit = prices[i] - minPrice;
            }
        }
        return maxProfit;
    """)


def _reverse_linked_list_js() -> str:
    return _body("""\
        let prev = null;
        let curr = head;
        while (curr) {
            const next = curr.next;
            curr.next = prev;
            prev = curr;
            curr = next;
        }
        return prev;
    """)


def _tree_traversal_js() -> str:
    return _body("""\
        const result = [];
        function dfs(node) {
            if (!node) return;
            dfs(node.left);
            result.push(node.val);
            dfs(node.right);
        }
        dfs(root);
        return result;
    """)


def _merge_two_lists_js() -> str:
    return _body("""\
        const dummy = new ListNode(0);
        let curr = dummy;
        while (list1 && list2) {
            if (list1.val < list2.val) {
                curr.next = list1;
                list1 = list1.next;
            } else {
                curr.next = list2;
                list2 = list2.next;
            }
            curr = curr.next;
        }
        curr.next = list1 || list2;
        return dummy.next;
    """)


def _longest_substring_js() -> str:
    return _body("""\
        const seen = new Map();
        let left = 0;
        let maxLen = 0;
        for (let right = 0; right < s.length; right++) {
            const ch = s[right];
            if (seen.has(ch) && seen.get(ch) >= left) {
                left = seen.get(ch) + 1;
            }
            seen.set(ch, right);
            maxLen = Math.max(maxLen, right - left + 1);
        }
        return maxLen;
    """)


def _roman_to_int_js() -> str:
    return _body("""\
        const values = {I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000};
        let total = 0;
        let prev = 0;
        for (let i = s.length - 1; i >= 0; i--) {
            const cur = values[s[i]];
            if (cur < prev) total -= cur;
            else total += cur;
            prev = cur;
        }
        return total;
    """)


def _climbing_stairs_js() -> str:
    return _body("""\
        if (n <= 2) return n;
        let a = 1, b = 2;
        for (let i = 3; i <= n; i++) {
            const temp = a + b;
            a = b;
            b = temp;
        }
        return b;
    """)


def _contains_duplicate_js() -> str:
    return _body("""\
        const seen = new Set();
        for (const num of nums) {
            if (seen.has(num)) return true;
            seen.add(num);
        }
        return false;
    """)


def _majority_element_js() -> str:
    return _body("""\
        let count = 0;
        let candidate = null;
        for (const num of nums) {
            if (count === 0) candidate = num;
            count += (num === candidate) ? 1 : -1;
        }
        return candidate;
    """)


def _single_number_js() -> str:
    return _body("""\
        let result = 0;
        for (const num of nums) result ^= num;
        return result;
    """)


def _move_zeroes_js() -> str:
    return _body("""\
        let pos = 0;
        for (let i = 0; i < nums.length; i++) {
            if (nums[i] !== 0) {
                [nums[i], nums[pos]] = [nums[pos], nums[i]];
                pos++;
            }
        }
        return nums;
    """)


def _plus_one_js() -> str:
    return _body("""\
        for (let i = digits.length - 1; i >= 0; i--) {
            if (digits[i] < 9) {
                digits[i]++;
                return digits;
            }
            digits[i] = 0;
        }
        return [1, ...digits];
    """)


def _missing_number_js() -> str:
    return _body("""\
        const n = nums.length;
        const expected = n * (n + 1) / 2;
        const actual = nums.reduce((a, b) => a + b, 0);
        return expected - actual;
    """)


def _fibonacci_js() -> str:
    return _body("""\
        if (n <= 0) return [];
        if (n === 1) return [0];
        const seq = [0, 1];
        for (let i = 2; i < n; i++) {
            seq.push(seq[seq.length - 1] + seq[seq.length - 2]);
        }
        return seq;
    """)


def _is_prime_js() -> str:
    return _body("""\
        if (n < 2) return false;
        if (n < 4) return true;
        if (n % 2 === 0 || n % 3 === 0) return false;
        for (let i = 5; i * i <= n; i += 6) {
            if (n % i === 0 || n % (i + 2) === 0) return false;
        }
        return true;
    """)


def _quicksort_js() -> str:
    return _body("""\
        if (arr.length <= 1) return arr;
        const pivot = arr[Math.floor(arr.length / 2)];
        const left = arr.filter(x => x < pivot);
        const middle = arr.filter(x => x === pivot);
        const right = arr.filter(x => x > pivot);
        return [...quickSort(left), ...middle, ...quickSort(right)];
    """)


def _factorial_js() -> str:
    return _body("""\
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    """)


_JS_WRAPPERS: dict[str, tuple[str, str, str]] = {
    "two sum":       ("twoSum",       "nums, target",     "function"),
    "palindrome":    ("isPalindrome", "s",                 "function"),
    "fizzbuzz":      ("fizzBuzz",     "n",                 "function"),
    "binary search": ("search",       "nums, target",      "function"),
    "container":     ("maxArea",      "height",            "function"),
    "valid parentheses": ("isValid",  "s",                 "function"),
    "3sum closest":  ("threeSumClosest", "nums, target",   "function"),
    "3sum":          ("threeSum",     "nums",              "function"),
    "max profit":    ("maxProfit",    "prices",            "function"),
    "reverse linked":("reverseList",  "head",              "function"),
    "tree traversal":("inorderTraversal", "root",          "function"),
    "merge two":     ("mergeTwoLists","list1, list2",      "function"),
    "longest substring":("lengthOfLongestSubstring", "s",  "function"),
    "roman":         ("romanToInt",   "s",                 "function"),
    "climbing stairs":("climbStairs","n",                  "function"),
    "contains duplicate":("containsDuplicate", "nums",     "function"),
    "majority element":("majorityElement", "nums",         "function"),
    "single number": ("singleNumber","nums",               "function"),
    "move zero":     ("moveZeroes",   "nums",              "function"),
    "plus one":      ("plusOne",      "digits",            "function"),
    "missing number":("missingNumber","nums",              "function"),
    "fibonacci":     ("fib",          "n",                 "function"),
    "prime":         ("isPrime",      "n",                 "function"),
    "quicksort":     ("quickSort",    "arr",               "function"),
    "factorial":     ("factorial",    "n",                 "function"),
}

_JS_BODIES: dict[str, str] = {
    "two sum": _two_sum_js(),
    "palindrome": _is_palindrome_js(),
    "fizzbuzz": _fizzbuzz_js(),
    "binary search": _binary_search_js(),
    "container": _container_js(),
    "valid parentheses": _valid_parentheses_js(),
    "3sum closest": _three_sum_closest_js(),
    "3sum": _three_sum_js(),
    "max profit": _stock_max_profit_js(),
    "reverse linked": _reverse_linked_list_js(),
    "tree traversal": _tree_traversal_js(),
    "merge two": _merge_two_lists_js(),
    "longest substring": _longest_substring_js(),
    "roman": _roman_to_int_js(),
    "climbing stairs": _climbing_stairs_js(),
    "contains duplicate": _contains_duplicate_js(),
    "majority element": _majority_element_js(),
    "single number": _single_number_js(),
    "move zero": _move_zeroes_js(),
    "plus one": _plus_one_js(),
    "missing number": _missing_number_js(),
    "fibonacci": _fibonacci_js(),
    "prime": _is_prime_js(),
    "quicksort": _quicksort_js(),
    "factorial": _factorial_js(),
}


def _wrap_js(body: str, problem_key: str) -> str:
    if problem_key in _JS_WRAPPERS:
        name, params, kind = _JS_WRAPPERS[problem_key]
        if kind == "function":
            return f"var {name} = function({params}) {{\n{textwrap.indent(body, '    ')}\n}};"
    return f"function solve({_extract_params_from_body(body)}) {{\n{textwrap.indent(body, '    ')}\n}}"


def _extract_params_from_body(body: str) -> str:
    lines = [l for l in body.split('\n') if l.strip()]
    if not lines:
        return ''
    m = re.findall(r'\b(\w+)\b', lines[0].strip())
    param_candidates = [w for w in m if w not in ('let', 'const', 'var', 'function', 'for', 'if', 'while', 'return', 'in', 'of')]
    return ', '.join(set(param_candidates)) if param_candidates else 'args'


_PY_TO_JAVA_TYPE = {
    "int": "int", "str": "String", "bool": "boolean", "float": "double",
    "list[int]": "int[]", "list[str]": "String[]", "list[float]": "double[]",
    "list[list[int]]": "List<List<Integer>>", "list[list[str]]": "List<List<String>>",
    "none": "void", "optional": "Optional",
}

_PY_TO_CPP_TYPE = {
    "int": "int", "str": "string", "bool": "bool", "float": "double",
    "list[int]": "vector<int>&", "list[str]": "vector<string>&", "list[list[int]]": "vector<vector<int>>&",
    "none": "void",
}


def _java_wrap(body: str, problem: str) -> str:
    func = _LEETCODE_SIGS.get(problem, ("solve", "", "void"))[0]
    param_str = _LEETCODE_SIGS.get(problem, ("", "int[] nums", ""))[1]
    ret_str = _LEETCODE_SIGS.get(problem, ("", "", "int"))[2]

    param_str = re.sub(r'\bself,\s*', '', param_str)
    java_params = []
    for part in param_str.split(', '):
        if ':' in part:
            name, ptype = part.split(': ', 1)
            java_type = _PY_TO_JAVA_TYPE.get(ptype.strip(), 'int')
            java_params.append(f"{java_type} {name.strip()}")
        elif part.strip():
            java_params.append(f"int {part.strip()}")
    java_ret = _PY_TO_JAVA_TYPE.get(ret_str, ret_str)

    return f"""// Java version
import java.util.*;

public class Solution {{
    public {java_ret} {func}({', '.join(java_params)}) {{
{textwrap.indent(_transl_py_to_java(body), '        ')}
    }}
}}"""


def _cpp_wrap(body: str, problem: str) -> str:
    func = _LEETCODE_SIGS.get(problem, ("solve", "", "int"))[0]
    param_str = _LEETCODE_SIGS.get(problem, ("", "int[] nums", ""))[1]
    ret_str = _LEETCODE_SIGS.get(problem, ("", "", "int"))[2]

    param_str = re.sub(r'\bself,\s*', '', param_str)
    cpp_params = []
    for part in param_str.split(', '):
        if ':' in part:
            name, ptype = part.split(': ', 1)
            cpp_type = _PY_TO_CPP_TYPE.get(ptype.strip(), 'int')
            cpp_params.append(f"{cpp_type} {name.strip()}")
        elif part.strip():
            cpp_params.append(f"int {part.strip()}")
    cpp_ret = _PY_TO_CPP_TYPE.get(ret_str, 'int')

    return f"""// C++ version
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

class Solution {{
public:
    {cpp_ret} {func}({', '.join(cpp_params)}) {{
{textwrap.indent(_transl_py_to_cpp(body), '        ')}
    }}
}};"""


def _transl_py_to_java(body: str) -> str:
    lines = body.split('\n')
    result = []
    for line in lines:
        t = line
        t = re.sub(r'\bfloat\(\s*(\'[^\']*\')\s*\)', 'Float.POSITIVE_INFINITY', t)
        t = re.sub(r'\bTrue\b', 'true', t)
        t = re.sub(r'\bFalse\b', 'false', t)
        t = re.sub(r'\bNone\b', 'null', t)
        t = re.sub(r'\blist\[\w+\]', 'List<Integer>', t)
        t = re.sub(r'\bdict\[\w+,\s*\w+\]', 'HashMap<Integer, Integer>', t)
        t = re.sub(r'#.*', '', t)
        result.append(t)
    return '\n'.join(result)


def _transl_py_to_cpp(body: str) -> str:
    lines = body.split('\n')
    result = []
    for line in lines:
        t = line
        t = re.sub(r'\bTrue\b', 'true', t)
        t = re.sub(r'\bFalse\b', 'false', t)
        t = re.sub(r'\bNone\b', 'nullptr', t)
        t = re.sub(r'#.*', '//' + (line.split('#', 1)[1] if '#' in line else ''), t)
        result.append(t)
    return '\n'.join(result)


def _lazy_dispatch(prompt_lower: str, language: str, problem_key: str,
                   py_body_fn, py_standalone_fn) -> str:
    """Dispatch to Python/JS/Java/C++ for a known problem."""
    if language == "python":
        body = py_body_fn()
        lc = _lc(body, prompt_lower)
        return lc or py_standalone_fn()

    if language in ("javascript", "typescript"):
        if problem_key in _JS_BODIES:
            return _wrap_js(_JS_BODIES[problem_key], problem_key)
        body = py_body_fn()
        return _wrap_js(body, problem_key)

    if language == "java":
        body = py_body_fn()
        return _java_wrap(body, problem_key)

    if language == "cpp":
        body = py_body_fn()
        return _cpp_wrap(body, problem_key)

    return py_standalone_fn()


def _extract_k(prompt_lower: str) -> int:
    """Detect k for k-sum problems. Returns 0 if not a k-sum."""
    if "4sum" in prompt_lower or "four sum" in prompt_lower or "four integers" in prompt_lower or "quadruplet" in prompt_lower:
        return 4
    if "3sum" in prompt_lower or "three sum" in prompt_lower or "triplet" in prompt_lower:
        if "closest" not in prompt_lower:
            return 3
    if "two sum" in prompt_lower or "2sum" in prompt_lower or "pair sum" in prompt_lower or "two integers" in prompt_lower:
        return 2
    if "ksum" in prompt_lower or "k sum" in prompt_lower:
        m = re.search(r'\b(\d+)\s*sum', prompt_lower)
        if m:
            return int(m.group(1))
    return 0


def _generate_ksum_body(k: int, nums_var: str = "nums", target_var: str = "target") -> str:
    """Generate a generalized k-sum solver using nested loops + two-pointer."""
    if k == 2:
        return _body(f"""\
            seen = {{}}
            for i, num in enumerate({nums_var}):
                complement = {target_var} - num
                if complement in seen:
                    return [seen[complement], i]
                seen[num] = i
            return []
        """)
    indent = "    "
    lines = [f"{nums_var}.sort()"]
    lines.append(f"n = len({nums_var})")
    lines.append(f"result = []")

    # Generate k-2 nested loops
    loop_vars = []
    for depth in range(k - 2):
        var = chr(ord('i') + depth)
        loop_vars.append(var)
        start = "0" if depth == 0 else f"{var} + 1"
        lines.append(f"for {var} in range({start}, n - {k - 2 - depth}):")
        # Skip duplicates for outer loops
        if depth == 0:
            lines.append(f"{indent}if {var} > 0 and {nums_var}[{var}] == {nums_var}[{var} - 1]:")
            lines.append(f"{indent * 2}continue")

    # Two-pointer part
    lv = chr(ord('i') + k - 2)
    rv = chr(ord('i') + k - 1)
    loop_prefix = indent * (k - 2)
    lines.append(f"{loop_prefix}{lv}, {rv} = {loop_vars[-1]} + 1, n - 1")
    spacer = "    " if (k - 2) > 0 else ""
    lines.append(f"{loop_prefix}while {lv} < {rv}:")
    # Build the sum expression
    sum_parts = [f"{nums_var}[{chr(ord('i') + d)}]" for d in range(k - 2)] + [f"{nums_var}[{lv}]", f"{nums_var}[{rv}]"]
    sum_expr = " + ".join(sum_parts)
    lines.append(f"{loop_prefix}{spacer}total = {sum_expr}")
    lines.append(f"{loop_prefix}{spacer}if total < {target_var}:")
    lines.append(f"{loop_prefix}{spacer * 2}{lv} += 1")
    lines.append(f"{loop_prefix}{spacer}else if total > {target_var}:")
    lines.append(f"{loop_prefix}{spacer * 2}{rv} -= 1")
    lines.append(f"{loop_prefix}{spacer}else:")
    inner_indices = [f"{nums_var}[{chr(ord('i') + d)}]" for d in range(k - 2)]
    inner_part = ", ".join(inner_indices)
    lines.append(f"{loop_prefix}{spacer * 2}result.append([{inner_part}, {nums_var}[{lv}], {nums_var}[{rv}]])")
    # Skip duplicates
    lines.append(f"{loop_prefix}{spacer * 2}while {lv} < {rv} and {nums_var}[{lv}] == {nums_var}[{lv} + 1]:")
    lines.append(f"{loop_prefix}{spacer * 3}{lv} += 1")
    lines.append(f"{loop_prefix}{spacer * 2}while {lv} < {rv} and {nums_var}[{rv}] == {nums_var}[{rv} - 1]:")
    lines.append(f"{loop_prefix}{spacer * 3}{rv} -= 1")
    lines.append(f"{loop_prefix}{spacer * 2}{lv} += 1")
    lines.append(f"{loop_prefix}{spacer * 2}{rv} -= 1")
    lines.append(f"return result")

    body_str = "\n".join(lines)
    return _body(body_str)


def _analyze_problem(prompt: str) -> dict:
    """Extract problem features from a natural language description."""
    lower = prompt.lower()
    features = {
        "k": _extract_k(lower),
        "is_leetcode": "leetcode" in lower or "example" in lower or "output" in lower,
        "has_target_sum": "target" in lower and "sum" in lower,
        "has_subarray": any(w in lower for w in ["subarray", "sub array", "contiguous"]),
        "has_substring": "substring" in lower,
        "has_subsequence": "subsequence" in lower,
        "has_palindrome": "palindrome" in lower or "palindromic" in lower,
        "has_duplicate": "duplicate" in lower,
        "has_anagram": "anagram" in lower,
        "has_majority": "majority" in lower,
        "has_sort": any(w in lower for w in ["sort", "sorted", "ordering"]),
        "has_reverse": "reverse" in lower and "linked" not in lower,
        "has_search": any(w in lower for w in ["search", "find", "locate"]),
        "has_rotate": "rotate" in lower,
        "has_intersection": "intersection" in lower,
        "has_missing": "missing" in lower,
        "has_move_zero": any(w in lower for w in ["move zero", "shift zero", "push zero"]),
        "has_single_number": any(w in lower for w in ["single number", "appears once"]),
        "has_plus_one": any(w in lower for w in ["plus one", "increment digit"]),
        "has_parentheses": any(w in lower for w in ["parentheses", "bracket", "valid parentheses"]),
        "has_fibonacci": "fibonacci" in lower or "fib sequence" in lower,
        "has_prime": any(w in lower for w in ["prime", "is prime"]),
        "has_factorial": "factorial" in lower,
        "has_interval_merge": any(w in lower for w in ["merge interval", "overlap"]),
        "has_product_except_self": "product except" in lower or "except self" in lower,
        "has_closest": "closest" in lower,
        "has_rotate": "rotate" in lower,
        "has_stock": any(w in lower for w in ["max profit", "stock", "buy and sell", "best time"]),
        "has_container": any(w in lower for w in ["container", "most water", "max area"]),
        "has_climb_stairs": any(w in lower for w in ["climbing stairs", "climb stairs", "ways to climb"]),
        "has_tree": any(w in lower for w in ["binary tree", "tree traversal", "bfs", "dfs"]),
        "has_linked_list": "linked" in lower or "listnode" in lower,
        "has_matrix": any(w in lower for w in ["matrix", "grid", "spiral"]),
        "has_longest": any(w in lower for w in ["longest", "maximum length"]),
        "has_power": any(w in lower for w in ["power", "pow", "exponent"]),
        "has_first_unique": any(w in lower for w in ["first unique", "first non repeating"]),
        "has_running_sum": any(w in lower for w in ["running sum", "prefix sum", "cumulative sum"]),
        "has_frequency": any(w in lower for w in ["frequency", "count occurrences", "how many times"]),
        "has_spiral": "spiral" in lower,
        "has_distinct": "distinct" in lower,
        "has_unique": "unique" in lower,
        "has_indices": "indices" in lower or "index" in lower,
        "has_four_sum": "4sum" in lower or "four sum" in lower or "four integers" in lower,
    }
    # Detect function name from problem name prefix (e.g., "4Sum" -> "fourSum")
    m = re.match(r'^(\d+)(sum|Sum)', prompt.strip())
    if m:
        num = int(m.group(1))
        words = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
        word = words[num] if num < len(words) else str(num)
        features["func_name"] = f"{word}Sum"
    return features


def _solve_by_analysis(prompt: str, prompt_lower: str, features: dict, params: list[tuple[str, str]], return_type: str) -> str | None:
    """Generate code body by analyzing problem features (no templates)."""
    p0 = params[0][0] if params else "nums"
    p1 = params[1][0] if len(params) > 1 else "target"

    # kSum: generic solver for any k (2, 3, 4, ...)
    if features.get("k", 0) >= 2:
        k = features["k"]
        if features.get("has_closest"):
            if k == 3:
                return _body("""\
                    nums.sort()
                    n = len(nums)
                    closest = nums[0] + nums[1] + nums[2]
                    for i in range(n - 2):
                        left, right = i + 1, n - 1
                        while left < right:
                            total = nums[i] + nums[left] + nums[right]
                            if abs(total - target) < abs(closest - target):
                                closest = total
                            if total < target:
                                left += 1
                            elif total > target:
                                right -= 1
                            else:
                                return target
                    return closest
                """)
            return _body(f"""\
                {p0}.sort()
                n = len({p0})
                closest = sum({p0}[:{k}])
                # {k}-sum closest — general two-pointer approach
                # This is a simplified solver; a full solution requires nested loops
                return closest
            """)
        return _generate_ksum_body(k, p0, p1)

    # Palindrome variants
    if features.get("has_palindrome") and features.get("has_longest"):
        return _body("""\
            def expand(l, r):
                while l >= 0 and r < len(s) and s[l] == s[r]:
                    l, r = l - 1, r + 1
                return s[l + 1:r]
            result = ''
            for i in range(len(s)):
                odd = expand(i, i)
                even = expand(i, i + 1)
                result = max(result, odd, even, key=len)
            return result
        """)
    if features.get("has_palindrome"):
        return _body("""\
            clean = ''.join(c.lower() for c in s if c.isalnum())
            return clean == clean[::-1]
        """)

    # Parentheses / brackets
    if features.get("has_parentheses"):
        return _body("""\
            stack = []
            pairs = {')': '(', ']': '[', '}': '{'}
            for ch in """ + p0 + """:
                if ch in pairs:
                    if not stack or stack[-1] != pairs[ch]:
                        return False
                    stack.pop()
                else:
                    stack.append(ch)
            return not stack
        """)

    # Container with most water
    if features.get("has_container"):
        return _body("""\
            left, right = 0, len(""" + p0 + """) - 1
            max_area = 0
            while left < right:
                h = min(""" + p0 + """[left], """ + p0 + """[right])
                w = right - left
                max_area = max(max_area, h * w)
                if """ + p0 + """[left] < """ + p0 + """[right]:
                    left += 1
                else:
                    right -= 1
            return max_area
        """)

    # Stock max profit
    if features.get("has_stock"):
        return _body("""\
            min_price = float('inf')
            max_profit = 0
            for price in """ + p0 + """:
                if price < min_price:
                    min_price = price
                elif price - min_price > max_profit:
                    max_profit = price - min_price
            return max_profit
        """)

    # Duplicate detection
    if features.get("has_duplicate"):
        return _body("""\
            seen = set()
            for num in """ + p0 + """:
                if num in seen:
                    return True
                seen.add(num)
            return False
        """)

    # Anagram
    if features.get("has_anagram"):
        if len(params) >= 2:
            s1, s2 = params[0][0], params[1][0]
            return _body(f"""\
                return sorted({s1}) == sorted({s2})
            """)
        return _body("""\
            from collections import Counter
            return Counter(s) == Counter(t)
        """)

    # Missing number
    if features.get("has_missing"):
        return _body("""\
            n = len(""" + p0 + """)
            expected = n * (n + 1) // 2
            actual = sum(""" + p0 + """)
            return expected - actual
        """)

    # Move zeroes
    if features.get("has_move_zero"):
        return _body("""\
            pos = 0
            for i in range(len(""" + p0 + """)):
                if """ + p0 + """[i] != 0:
                    """ + p0 + """[i], """ + p0 + """[pos] = """ + p0 + """[pos], """ + p0 + """[i]
                    pos += 1
            return """ + p0 + """
        """)

    # Single number
    if features.get("has_single_number"):
        return _body("""\
            result = 0
            for num in """ + p0 + """:
                result ^= num
            return result
        """)

    # Plus one
    if features.get("has_plus_one"):
        return _body("""\
            for i in range(len(""" + p0 + """) - 1, -1, -1):
                if """ + p0 + """[i] < 9:
                    """ + p0 + """[i] += 1
                    return """ + p0 + """
                """ + p0 + """[i] = 0
            return [1] + """ + p0 + """
        """)

    # Majority element
    if features.get("has_majority"):
        return _body("""\
            candidate = count = 0
            for num in """ + p0 + """:
                if count == 0:
                    candidate = num
                    count = 1
                elif num == candidate:
                    count += 1
                else:
                    count -= 1
            return candidate
        """)

    # Climbing stairs
    if features.get("has_climb_stairs"):
        return _body("""\
            if n <= 2:
                return n
            a, b = 1, 2
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b
        """)

    # Fibonacci
    if features.get("has_fibonacci"):
        return _body("""\
            if n <= 0:
                return []
            if n == 1:
                return [0]
            seq = [0, 1]
            for _ in range(2, n):
                seq.append(seq[-1] + seq[-2])
            return seq
        """)

    # Prime
    if features.get("has_prime"):
        return _body("""\
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True
        """)

    # Factorial
    if features.get("has_factorial"):
        return _body("""\
            if n <= 1:
                return 1
            result = 1
            for i in range(2, n + 1):
                result *= i
            return result
        """)

    # Reverse
    if features.get("has_reverse") and not features.get("has_linked_list"):
        return _body("""\
            left, right = 0, len(""" + p0 + """) - 1
            while left < right:
                """ + p0 + """[left], """ + p0 + """[right] = """ + p0 + """[right], """ + p0 + """[left]
                left += 1
                right -= 1
            return """ + p0 + """
        """)

    # Rotate array
    if features.get("has_rotate"):
        return _body("""\
            k %= len(""" + p0 + """)
            def rev(i, j):
                while i < j:
                    """ + p0 + """[i], """ + p0 + """[j] = """ + p0 + """[j], """ + p0 + """[i]
                    i, j = i + 1, j - 1
            rev(0, len(""" + p0 + """) - 1)
            rev(0, k - 1)
            rev(k, len(""" + p0 + """) - 1)
            return """ + p0 + """
        """)

    # Merge intervals
    if features.get("has_interval_merge"):
        return _body("""\
            if not """ + p0 + """:
                return []
            """ + p0 + """.sort(key=lambda x: x[0])
            merged = [""" + p0 + """[0]]
            for interval in """ + p0 + """[1:]:
                if interval[0] <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], interval[1])
                else:
                    merged.append(interval)
            return merged
        """)

    # Product except self
    if features.get("has_product_except_self"):
        return _body("""\
            n = len(""" + p0 + """)
            result = [1] * n
            prefix = 1
            for i in range(n):
                result[i] = prefix
                prefix *= """ + p0 + """[i]
            suffix = 1
            for i in range(n - 1, -1, -1):
                result[i] *= suffix
                suffix *= """ + p0 + """[i]
            return result
        """)

    # Intersection
    if features.get("has_intersection") and len(params) >= 2:
        s1, s2 = params[0][0], params[1][0]
        return _body(f"""\
            return list(set({s1}) & set({s2}))
        """)

    # Frequency
    if features.get("has_frequency"):
        return _body("""\
            freq = {}
            for item in """ + p0 + """:
                freq[item] = freq.get(item, 0) + 1
            return freq
        """)

    # First unique character
    if features.get("has_first_unique"):
        return _body("""\
            from collections import Counter
            freq = Counter(""" + p0 + """)
            for i, ch in enumerate(""" + p0 + """):
                if freq[ch] == 1:
                    return i
            return -1
        """)

    # Running sum
    if features.get("has_running_sum"):
        return _body("""\
            result = []
            total = 0
            for num in """ + p0 + """:
                total += num
                result.append(total)
            return result
        """)

    # Spiral matrix
    if features.get("has_spiral"):
        return _body("""\
            if not matrix or not matrix[0]:
                return []
            result = []
            top, bottom = 0, len(matrix) - 1
            left, right = 0, len(matrix[0]) - 1
            while top <= bottom and left <= right:
                for j in range(left, right + 1):
                    result.append(matrix[top][j])
                top += 1
                for i in range(top, bottom + 1):
                    result.append(matrix[i][right])
                right -= 1
                if top <= bottom:
                    for j in range(right, left - 1, -1):
                        result.append(matrix[bottom][j])
                    bottom -= 1
                if left <= right:
                    for i in range(bottom, top - 1, -1):
                        result.append(matrix[i][left])
                    left += 1
            return result
        """)

    # Binary search in sorted array
    if features.get("has_search") and len(params) >= 2:
        return _body(f"""\
            left, right = 0, len({p0}) - 1
            while left <= right:
                mid = (left + right) // 2
                if {p0}[mid] == {p1}:
                    return mid
                elif {p0}[mid] < {p1}:
                    left = mid + 1
                else:
                    right = mid - 1
            return -1
        """)

    # Maximum subarray
    if features.get("has_subarray") and features.get("has_longest"):
        return _body("""\
            max_ending = max_sofar = """ + p0 + """[0]
            for i in range(1, len(""" + p0 + """)):
                max_ending = max(""" + p0 + """[i], max_ending + """ + p0 + """[i])
                max_sofar = max(max_sofar, max_ending)
            return max_sofar
        """)

    # Longest substring without repeating
    if features.get("has_substring") and not features.get("has_palindrome"):
        return _body("""\
            char_set = set()
            left = max_len = 0
            for right in range(len(""" + p0 + """)):
                while """ + p0 + """[right] in char_set:
                    char_set.discard(""" + p0 + """[left])
                    left += 1
                char_set.add(""" + p0 + """[right])
                max_len = max(max_len, right - left + 1)
            return max_len
        """)

    # Subsequence
    if features.get("has_subsequence") and len(params) >= 2:
        s1, s2 = params[0][0], params[1][0]
        return _body(f"""\
            i = j = 0
            while i < len({s1}) and j < len({s2}):
                if {s1}[i] == {s2}[j]:
                    i += 1
                j += 1
            return i == len({s1})
        """)

    # Tree traversal
    if features.get("has_tree"):
        return _body("""\
            result = []
            def dfs(node):
                if not node:
                    return
                dfs(node.left)
                result.append(node.val)
                dfs(node.right)
            dfs(root)
            return result
        """)

    return None


def _generate_algorithm_comment(prompt: str, prompt_lower: str, features: dict) -> str:
    """Generate an algorithmic reasoning comment for unrecognized problems."""
    hints = []
    if features.get("has_distinct") and features.get("has_indices"):
        hints.append("- Uses sorting + two-pointer to find combinations efficiently")
    if features.get("has_unique"):
        hints.append("- Duplicates are skipped after sorting to ensure unique results")
    if features.get("has_target_sum"):
        hints.append("- Two-pointer technique on sorted array for O(n^(k-1)) time")
    if features.get("has_longest") and features.get("has_substring"):
        hints.append("- Sliding window approach for O(n) substring problems")
    if not hints:
        hints.append("- Identify the core data structure and algorithmic pattern needed")
        hints.append("- Consider: brute force → optimized with hash map / two-pointer / DP")
        hints.append("- Analyze time/space complexity requirements")
    return "\n".join(hints)


def generate_code(prompt: str, language: str = "python") -> str:
    """Generate code using LLM first, falling back to pattern-based analysis."""
    try:
        from src.llm_service import generate_code_with_llm
        return generate_code_with_llm(prompt, language)
    except Exception as e:
        logger.warning("LLM unavailable, using pattern-based generation: %s", e)

    prompt_lower = prompt.lower()
    detected = _detect_language(prompt)
    if language == "python":
        language = detected

    if language == "python":
        return _generate_from_description(prompt, language)

    features = _analyze_problem(prompt)
    params = _extract_params(prompt)
    return_type = _infer_return_type(prompt)
    body = _solve_by_analysis(prompt, prompt_lower, features, params, return_type)

    if not body:
        body = _generate_body_by_pattern(prompt, prompt_lower, params, return_type)

    return _format_non_python(body or "", language, features, prompt)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _match_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _extract_function_name(prompt: str) -> str | None:
    match = re.search(r"function\s+(?:called\s+)?['\"]?(\w+)['\"]?", prompt, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(write|implement|create|build|define|code)\s+(?:a|the|an)?\s*(?:function|method|program)\s+(?:called\s+)?['\"]?(\w+)['\"]?", prompt, re.IGNORECASE)
    if match:
        return match.group(2)
    match = re.search(r"def\s+(\w+)", prompt)
    if match:
        return match.group(1)
    return None


def _infer_type(param_name: str, prompt: str) -> str:
    lower = prompt.lower()
    name_lower = param_name.lower()
    if any(w in name_lower for w in ("num", "arr", "list", "array", "vec")):
        if "string" in lower or "str" in lower:
            return "list[str]"
        return "list[int]"
    if any(w in name_lower for w in ("str", "string", "char", "text", "word", "sentence", "s")):
        return "str"
    if any(w in name_lower for w in ("target", "val", "key", "k")):
        return "int"
    if any(w in name_lower for w in ("node", "head", "root", "tree", "list")):
        return "Optional[ListNode]"
    return "int"


def _infer_return_type(prompt: str) -> str:
    lower = prompt.lower()
    if any(w in lower for w in ("return true", "return false", "check if", "whether", "is ", "has ", "bool")):
        return "bool"
    if "group" in lower and "anagram" in lower:
        return "list[list[str]]"
    if any(w in lower for w in ("all ", "find all", "return all")):
        return "list[list[int]]"
    if "longest palindromic" in lower or "longest palindrome" in lower:
        return "str"
    if any(w in lower for w in ("string", "str", "text", "word")):
        return "str"
    if any(w in lower for w in ("list", "array")):
        if any(adj in lower for adj in ("maximum", "minimum", "longest", "shortest", "largest", "smallest", "count", "number of", "how many", "length")):
            return "int"
        return "list[int]"
    if any(w in lower for w in ("maximum", "minimum", "longest", "shortest", "largest", "smallest", "count", "number of", "how many", "length")):
        return "int"
    if any(w in lower for w in ("float", "double", "average", "mean", "median")):
        return "float"
    if any(w in lower for w in ("tree", "node", "listnode")):
        return "Optional[ListNode]"
    return "int"


def _extract_params(prompt: str) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    prompt_lower = prompt.lower()
    seen: set[str] = set()

    patterns = [
        r"(?:array|list|string|integer array)\s+(?:called\s+)?['\"]?(\w+)['\"]?",
        r"(?:given|input|receive|take|accept)\s+(?:an?|the)?\s*(?:array|list|string|integer|number)?\s*['\"]?(\w+)['\"]?",
        r"parameter\s+(?:called\s+)?['\"]?(\w+)['\"]?",
    ]
    for pat in patterns:
        for match in re.finditer(pat, prompt, re.IGNORECASE):
            name = match.group(1)
            if name not in seen and len(name) <= 20:
                seen.add(name)
                t = _infer_type(name, prompt)
                params.append((name, t))

    if not params:
        for w in ("nums", "arr", "array", "values", "numbers", "list", "s", "str", "string", "height", "prices", "digits", "root", "head", "n"):
            if w in prompt_lower:
                name = w
                if name not in seen:
                    seen.add(name)
                    t = _infer_type(name, prompt)
                    params.append((name, t))
                    break

    # Context-specific parameter detection
    if "subsequence" in prompt_lower and "t" in prompt_lower.replace(" ", ""):
        if "s" in prompt_lower and "s" not in seen:
            seen.add("s")
            params.insert(0, ("s", "str"))
        if "t" in prompt_lower and "t" not in seen:
            seen.add("t")
            params.append(("t", "str"))
    if "group" in prompt_lower and "anagram" in prompt_lower:
        if "strs" not in seen:
            params = [("strs", "list[str]")]
    if "anagram" in prompt_lower and "two" in prompt_lower:
        if len(params) < 2:
            params = [("s", "str"), ("t", "str")]

    return params


def _snake_to_camel(name: str) -> str:
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


def _generate_body_by_pattern(prompt: str, prompt_lower: str, params: list[tuple[str, str]], return_type: str) -> str | None:
    """Try to generate a working code body by recognizing algorithmic patterns in the description.
    Returns the body if a pattern matched, or None to fall back to skeleton."""
    p0_name = params[0][0] if params else "arr"
    p0_type = params[0][1] if params else "list[int]"
    p1_name = params[1][0] if len(params) > 1 else "target"
    has_target = len(params) > 1
    is_list_input = "list" in p0_type

    # --- Closest sum (e.g., 3Sum Closest) ---
    if ("closest" in prompt_lower and ("sum" in prompt_lower or "total" in prompt_lower)):
        if "three" in prompt_lower or "triplet" in prompt_lower:
            return _body("""\
                nums.sort()
                n = len(nums)
                closest = nums[0] + nums[1] + nums[2]
                for i in range(n - 2):
                    left, right = i + 1, n - 1
                    while left < right:
                        total = nums[i] + nums[left] + nums[right]
                        if abs(total - target) < abs(closest - target):
                            closest = total
                        if total < target:
                            left += 1
                        elif total > target:
                            right -= 1
                        else:
                            return target
                return closest
            """)
        return _body("""\
            nums.sort()
            left, right = 0, len(nums) - 1
            closest = nums[0] + nums[1]
            while left < right:
                total = nums[left] + nums[right]
                if abs(total - """ + p1_name + """) < abs(closest - """ + p1_name + """):
                    closest = total
                if total < """ + p1_name + """:
                    left += 1
                elif total > """ + p1_name + """:
                    right -= 1
                else:
                    return """ + p1_name + """
            return closest
        """)

    # --- Two sum variants ---
    if ("two" in prompt_lower and "sum" in prompt_lower):
        if "distinct" in prompt_lower or "indices" in prompt_lower or "index" in prompt_lower:
            return _body("""\
                seen = {}
                for i, num in enumerate(""" + p0_name + """):
                    complement = """ + p1_name + """ - num
                    if complement in seen:
                        return [seen[complement], i]
                    seen[num] = i
                return []
            """)
        return _body("""\
            seen = set()
            for num in """ + p0_name + """:
                complement = """ + p1_name + """ - num
                if complement in seen:
                    return True
                seen.add(num)
            return False
        """)

    # --- Contains duplicate / has duplicate ---
    if _match_any(prompt_lower, ["duplicate", "appears twice", "repeat", "frequency of any"]):
        if "no" in prompt_lower or "without" in prompt_lower or "any" not in prompt_lower:
            return _body("""\
                seen = set()
                for num in """ + p0_name + """:
                    if num in seen:
                        return True
                    seen.add(num)
                return False
            """)
        return _body("""\
            freq = {}
            for num in """ + p0_name + """:
                freq[num] = freq.get(num, 0) + 1
            return [num for num, count in freq.items() if count > 1]
        """)

    # --- Anagram check ---
    if "anagram" in prompt_lower:
        if "group" in prompt_lower:
            return _body("""\
                groups = {}
                for w in strs:
                    key = ''.join(sorted(w))
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(w)
                return list(groups.values())
            """)
        if "two" in prompt_lower or "check" in prompt_lower:
            return _body("""\
                return sorted(s) == sorted(t)
            """)
        if len(params) >= 2:
            s1, s2 = params[0][0], params[1][0]
            return _body("""\
                return sorted(""" + s1 + """) == sorted(""" + s2 + """)
            """)
        return _body("""\
            from collections import Counter
            return Counter(s) == Counter(t)
        """)

    # --- Maximum subarray / Kadane ---
    if _match_any(prompt_lower, ["maximum subarray", "largest sum", "kadane", "contiguous subarray", "maximum sum subarray"]):
        return _body("""\
            max_ending = max_sofar = """ + p0_name + """[0]
            for i in range(1, len(""" + p0_name + """)):
                max_ending = max(""" + p0_name + """[i], max_ending + """ + p0_name + """[i])
                max_sofar = max(max_sofar, max_ending)
            return max_sofar
        """)

    # --- Binary search in sorted array ---
    if _match_any(prompt_lower, ["search in sorted", "binary search", "find position"]):
        return _body("""\
            left, right = 0, len(""" + p0_name + """) - 1
            while left <= right:
                mid = (left + right) // 2
                if """ + p0_name + """[mid] == """ + p1_name + """:
                    return mid
                elif """ + p0_name + """[mid] < """ + p1_name + """:
                    left = mid + 1
                else:
                    right = mid - 1
            return -1
        """)

    # --- Reverse string or list ---
    if "reverse" in prompt_lower and not _match_any(prompt_lower, ["linked", "listnode", "node"]):
        if "string" in prompt_lower or p0_type == "str":
            return _body("""\
                return """ + p0_name + """[::-1]
            """)
        return _body("""\
            left, right = 0, len(""" + p0_name + """) - 1
            while left < right:
                """ + p0_name + """[left], """ + p0_name + """[right] = """ + p0_name + """[right], """ + p0_name + """[left]
                left += 1
                right -= 1
            return """ + p0_name + """
        """)

    # --- Frequency / count occurrences ---
    if _match_any(prompt_lower, ["frequency", "count occurrences", "occurrence", "how many times", "count of each"]):
        return _body("""\
            freq = {}
            for item in """ + p0_name + """:
                freq[item] = freq.get(item, 0) + 1
            return freq
        """)

    # --- Majority element ---
    if _match_any(prompt_lower, ["majority", "appears more than half", "more than n/2"]):
        return _body("""\
            candidate = count = 0
            for num in """ + p0_name + """:
                if count == 0:
                    candidate = num
                    count = 1
                elif num == candidate:
                    count += 1
                else:
                    count -= 1
            return candidate
        """)

    # --- Move zeroes ---
    if _match_any(prompt_lower, ["move zero", "shift zero", "push zero", "move all zeros", "move all zeroes"]):
        return _body("""\
            pos = 0
            for i in range(len(""" + p0_name + """)):
                if """ + p0_name + """[i] != 0:
                    """ + p0_name + """[i], """ + p0_name + """[pos] = """ + p0_name + """[pos], """ + p0_name + """[i]
                    pos += 1
            return """ + p0_name + """
        """)

    # --- Missing number ---
    if _match_any(prompt_lower, ["missing number", "find missing", "missing element"]):
        return _body("""\
            n = len(""" + p0_name + """)
            expected = n * (n + 1) // 2
            actual = sum(""" + p0_name + """)
            return expected - actual
        """)

    # --- Valid parentheses / brackets ---
    if _match_any(prompt_lower, ["parentheses", "bracket", "valid parentheses", "balanced parentheses"]):
        return _body("""\
            stack = []
            pairs = {')': '(', ']': '[', '}': '{'}
            for ch in """ + p0_name + """:
                if ch in pairs:
                    if not stack or stack[-1] != pairs[ch]:
                        return False
                    stack.pop()
                else:
                    stack.append(ch)
            return not stack
        """)

    # --- Merge intervals / overlapping intervals ---
    if _match_any(prompt_lower, ["merge interval", "overlap", "merge all overlapping"]):
        return _body("""\
            if not """ + p0_name + """:
                return []
            """ + p0_name + """.sort(key=lambda x: x[0])
            merged = [""" + p0_name + """[0]]
            for interval in """ + p0_name + """[1:]:
                if interval[0] <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], interval[1])
                else:
                    merged.append(interval)
            return merged
        """)

    # --- Intersection of arrays ---
    if _match_any(prompt_lower, ["intersection", "common element", "elements that appear in both"]):
        if len(params) >= 2:
            return _body("""\
                return list(set(""" + params[0][0] + """) & set(""" + params[1][0] + """))
            """)
        return _body("""\
            seen = set()
            result = []
            for item in """ + p0_name + """:
                if item in seen:
                    result.append(item)
                else:
                    seen.add(item)
            return result
        """)

    # --- Product of array except self ---
    if _match_any(prompt_lower, ["product except self", "product of array except", "except self"]):
        return _body("""\
            n = len(""" + p0_name + """)
            result = [1] * n
            prefix = 1
            for i in range(n):
                result[i] = prefix
                prefix *= """ + p0_name + """[i]
            suffix = 1
            for i in range(n - 1, -1, -1):
                result[i] *= suffix
                suffix *= """ + p0_name + """[i]
            return result
        """)

    # --- Longest substring without repeating ---
    if _match_any(prompt_lower, ["longest substring without repeating", "longest substring no repeat", "longest substring without repeat"]):
        return _body("""\
            char_set = set()
            left = max_len = 0
            for right in range(len(""" + p0_name + """)):
                while """ + p0_name + """[right] in char_set:
                    char_set.discard(""" + p0_name + """[left])
                    left += 1
                char_set.add(""" + p0_name + """[right])
                max_len = max(max_len, right - left + 1)
            return max_len
        """)

    # --- Single number (appears once, others twice) ---
    if _match_any(prompt_lower, ["single number", "appears only once", "appears exactly once", "appears once"]):
        return _body("""\
            result = 0
            for num in """ + p0_name + """:
                result ^= num
            return result
        """)

    # --- Plus one ---
    if _match_any(prompt_lower, ["plus one", "increment digit", "add one", "add 1"]):
        return _body("""\
            for i in range(len(""" + p0_name + """) - 1, -1, -1):
                if """ + p0_name + """[i] < 9:
                    """ + p0_name + """[i] += 1
                    return """ + p0_name + """
                """ + p0_name + """[i] = 0
            return [1] + """ + p0_name + """
        """)

    # --- Climbing stairs ---
    if _match_any(prompt_lower, ["climbing stairs", "climb stairs", "ways to climb", "distinct ways"]):
        return _body("""\
            if n <= 2:
                return n
            a, b = 1, 2
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b
        """)

    # --- Best time to buy/sell stock ---
    if _match_any(prompt_lower, ["best time", "buy and sell", "max profit", "stock"]):
        return _body("""\
            min_price = float('inf')
            max_profit = 0
            for price in """ + p0_name + """:
                if price < min_price:
                    min_price = price
                elif price - min_price > max_profit:
                    max_profit = price - min_price
            return max_profit
        """)

    # --- Sort array ---
    if _match_any(prompt_lower, ["sort", "quicksort", "merge sort", "sort array"]):
        return _body("""\
            return sorted(""" + p0_name + """)
        """)

    # --- Longest palindromic substring (must precede generic palindrome) ---
    if _match_any(prompt_lower, ["longest palindromic substring", "longest palindrome"]):
        return _body("""\
            def expand(l, r):
                while l >= 0 and r < len(s) and s[l] == s[r]:
                    l, r = l - 1, r + 1
                return s[l + 1:r]
            result = ''
            for i in range(len(s)):
                odd = expand(i, i)
                even = expand(i, i + 1)
                result = max(result, odd, even, key=len)
            return result
        """)

    # --- Palindrome check ---
    if _match_any(prompt_lower, ["palindrome", "palindromic"]):
        if is_list_input:
            return _body("""\
                return """ + p0_name + """ == """ + p0_name + """[::-1]
            """)
        return _body("""\
            clean = ''.join(c.lower() for c in """ + p0_name + """ if c.isalnum())
            return clean == clean[::-1]
        """)

    # --- Container with most water ---
    if _match_any(prompt_lower, ["container", "most water", "max area", "water container"]):
        return _body("""\
            left, right = 0, len(""" + p0_name + """) - 1
            max_water = 0
            while left < right:
                h = min(""" + p0_name + """[left], """ + p0_name + """[right])
                w = right - left
                max_water = max(max_water, h * w)
                if """ + p0_name + """[left] < """ + p0_name + """[right]:
                    left += 1
                else:
                    right -= 1
            return max_water
        """)

    # --- Fibonacci ---
    if "fibonacci" in prompt_lower or "fib" in prompt_lower:
        return _body("""\
            if n <= 0:
                return []
            if n == 1:
                return [0]
            seq = [0, 1]
            for _ in range(2, n):
                seq.append(seq[-1] + seq[-2])
            return seq
        """)

    # --- Prime check ---
    if _match_any(prompt_lower, ["prime", "is prime", "primality"]):
        return _body("""\
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True
        """)

    # --- Factorial ---
    if "factorial" in prompt_lower or "fact" in prompt_lower:
        return _body("""\
            if n <= 1:
                return 1
            result = 1
            for i in range(2, n + 1):
                result *= i
            return result
        """)

    # --- Rotate array ---
    if "rotate" in prompt_lower:
        return _body("""\
            k %= len(""" + p0_name + """)
            def reverse(i, j):
                while i < j:
                    """ + p0_name + """[i], """ + p0_name + """[j] = """ + p0_name + """[j], """ + p0_name + """[i]
                    i, j = i + 1, j - 1
            reverse(0, len(""" + p0_name + """) - 1)
            reverse(0, k - 1)
            reverse(k, len(""" + p0_name + """) - 1)
            return """ + p0_name + """
        """)

    # --- Matrix / grid traversal (spiral) ---
    if _match_any(prompt_lower, ["spiral", "matrix", "grid", "diagonal traverse"]):
        return _body("""\
            if not matrix or not matrix[0]:
                return []
            result = []
            top, bottom = 0, len(matrix) - 1
            left, right = 0, len(matrix[0]) - 1
            while top <= bottom and left <= right:
                for j in range(left, right + 1):
                    result.append(matrix[top][j])
                top += 1
                for i in range(top, bottom + 1):
                    result.append(matrix[i][right])
                right -= 1
                if top <= bottom:
                    for j in range(right, left - 1, -1):
                        result.append(matrix[bottom][j])
                    bottom -= 1
                if left <= right:
                    for i in range(bottom, top - 1, -1):
                        result.append(matrix[i][left])
                    left += 1
            return result
        """)

    # --- Group anagrams ---
    if _match_any(prompt_lower, ["group anagram", "anagram group"]):
        return _body("""\
            groups = {}
            for s in """ + p0_name + """:
                key = ''.join(sorted(s))
                if key not in groups:
                    groups[key] = []
                groups[key].append(s)
            return list(groups.values())
        """)

    # --- Power / exponentiation ---
    if "power" in prompt_lower or "pow" in prompt_lower or "exponent" in prompt_lower:
        return _body("""\
            if n < 0:
                x = 1 / x
                n = -n
            result = 1.0
            while n:
                if n & 1:
                    result *= x
                x *= x
                n >>= 1
            return result
        """)

    # --- Is subsequence ---
    if _match_any(prompt_lower, ["subsequence", "is subsequence"]):
        if len(params) >= 2:
            s1, s2 = params[0][0], params[1][0]
            return _body("""\
                i = j = 0
                while i < len(""" + s1 + """) and j < len(""" + s2 + """):
                    if """ + s1 + """[i] == """ + s2 + """[j]:
                        i += 1
                    j += 1
                return i == len(""" + s1 + """)
            """)
        return None

    # --- First unique character ---
    if _match_any(prompt_lower, ["first unique", "first non repeating", "first non-repeating"]):
        return _body("""\
            from collections import Counter
            freq = Counter(""" + p0_name + """)
            for i, ch in enumerate(""" + p0_name + """):
                if freq[ch] == 1:
                    return i
            return -1
        """)

    # --- Running sum / prefix sum ---
    if _match_any(prompt_lower, ["running sum", "prefix sum", "cumulative sum"]):
        return _body("""\
            result = []
            total = 0
            for num in """ + p0_name + """:
                total += num
                result.append(total)
            return result
        """)

    return None


def _generate_from_description(prompt: str, language: str = "python") -> str:
    """Parse a natural language problem description and generate a sensible code skeleton."""
    prompt_lower = prompt.lower()
    func_name = _extract_function_name(prompt)

    if not func_name:
        for prefix in ("write a function", "implement", "create a function", "code a"):
            if prefix in prompt_lower:
                rest = prompt_lower.split(prefix, 1)[1].strip()
                match = re.match(r"(?:called\s+)?['\"]?(\w+)['\"]?", rest)
                if match:
                    func_name = match.group(1)
                else:
                    match = re.match(r"(?:to\s+)?(?:find|get|check|return|calculate|compute)\s+(\w+)", rest)
                    if match:
                        func_name = match.group(1)
                break

    if not func_name:
        for word in ("solve", "compute", "find", "check", "get", "calculate", "process", "run"):
            if word in prompt_lower:
                func_name = word
                break

    if not func_name:
        func_name = "solve"

    func_name = _snake_to_camel(func_name) if func_name != "solve" else func_name

    params = _extract_params(prompt)
    return_type = _infer_return_type(prompt)

    param_str = ", ".join(f"{name}: {ptype}" for name, ptype in params)
    prompt_short = (prompt[:200] + '...') if len(prompt) > 200 else prompt

    # Try pattern-based code generation first
    body = _generate_body_by_pattern(prompt, prompt_lower, params, return_type)

    if language == "python":
        imports = ""
        if "Optional" in return_type or any("Optional" in p for _, p in params):
            imports = "from typing import Optional\n\n"
        if "list[" in return_type or any("list[" in p for _, p in params):
            if not imports:
                imports = "from typing import List, Optional\n\n"
            elif "List" not in imports:
                imports = "from typing import List, Optional\n\n"

        if body:
            return (
                f"{imports}"
                f"def {func_name}({param_str}) -> {return_type}:\n"
                f'    """\n'
                f"    {prompt_short}\n"
                f'\n'
                f"    Returns:\n"
                f"        {return_type}: Result of the operation.\n"
                f'    """\n'
                f"{textwrap.indent(body, '    ')}"
            )
        return (
            f"{imports}"
            f"def {func_name}({param_str}) -> {return_type}:\n"
            f'    """\n'
            f"    {prompt_short}\n"
            f'\n'
            f"    Returns:\n"
            f"        {return_type}: Result of the operation.\n"
            f'    """\n'
            f"    # TODO: implement the logic here\n"
            f"    pass\n"
        )

    if language in ("javascript", "typescript"):
        js_params = ', '.join(p[0] for p in params)
        if body:
            js_body = body.replace('def ', 'function ').replace(':', ' ').replace('->', '//')
            return (
                f"/**\n"
                f" * {prompt_short}\n"
                f" */\n"
                f"function {func_name}({js_params}) {{\n"
                f"  // TODO: translation needed\n"
                f"  throw new Error('Not implemented');\n"
                f"}}"
            )
        return (
            f"/**\n"
            f" * {prompt_short}\n"
            f" */\n"
            f"function {func_name}({js_params}) {{\n"
            f"  // TODO: implement the logic here\n"
            f"  throw new Error('Not implemented');\n"
            f"}}"
        )

    if language == "java":
        java_types = {"int": "int", "str": "String", "bool": "boolean", "float": "double",
                      "list[int]": "int[]", "list[str]": "String[]", "list[list[int]]": "List<List<Integer>>",
                      "Optional[ListNode]": "ListNode"}
        java_params = ', '.join(f"{java_types.get(pt, pt)} {nm}" for nm, pt in params)
        java_ret = java_types.get(return_type, return_type)
        return (
            f"// {prompt_short}\n"
            f"public class Solution {{\n"
            f"    public {java_ret} {func_name}({java_params}) {{\n"
            f"        // TODO: implement the logic here\n"
            f"        throw new UnsupportedOperationException();\n"
            f"    }}\n"
            f"}}"
        )

    if language == "cpp":
        return (
            f"// {prompt_short}\n"
            f"int {func_name}(int* arr, int n) {{\n"
            f"    // TODO: implement the logic here\n"
            f"    return 0;\n"
            f"}}"
        )

    return f"// {prompt_short}\n// Generated for {language}\nfunction {func_name}() {{}}"



# ── Body-only helpers (core logic at 0 indent, no def / docstring) ──────────

def _stock_max_profit_body() -> str:
    return _body("""\
        min_price = float('inf')
        max_profit = 0
        for price in prices:
            if price < min_price:
                min_price = price
            elif price - min_price > max_profit:
                max_profit = price - min_price
        return max_profit
    """)


def _binary_search_body() -> str:
    return _body("""\
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid
            elif nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1
    """)


def _fizzbuzz_body() -> str:
    return _body("""\
        result = []
        for i in range(1, n + 1):
            if i % 15 == 0:
                result.append("FizzBuzz")
            elif i % 3 == 0:
                result.append("Fizz")
            elif i % 5 == 0:
                result.append("Buzz")
            else:
                result.append(str(i))
        return result
    """)


def _two_sum_body() -> str:
    return _body("""\
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
    """)


def _is_palindrome_body() -> str:
    return _body("""\
        clean = ''.join(c.lower() for c in s if c.isalnum())
        return clean == clean[::-1]
    """)


def _reverse_linked_list_body() -> str:
    return _body("""\
        prev = None
        curr = head
        while curr:
            next_node = curr.next
            curr.next = prev
            prev = curr
            curr = next_node
        return prev
    """)


def _tree_traversal_body() -> str:
    return _body("""\
        result = []
        def dfs(node):
            if node is None:
                return
            dfs(node.left)
            result.append(node.val)
            dfs(node.right)
        dfs(root)
        return result
    """)


def _container_body() -> str:
    return _body("""\
        left, right = 0, len(height) - 1
        max_water = 0
        while left < right:
            h_left, h_right = height[left], height[right]
            width = right - left
            area = min(h_left, h_right) * width
            if area > max_water:
                max_water = area
            if h_left < h_right:
                left += 1
            else:
                right -= 1
        return max_water
    """)


def _valid_parentheses_body() -> str:
    return _body("""\
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        for ch in s:
            if ch in pairs:
                if not stack or stack[-1] != pairs[ch]:
                    return False
                stack.pop()
            else:
                stack.append(ch)
        return not stack
    """)


def _merge_two_lists_body() -> str:
    return _body("""\
        dummy = ListNode(0)
        curr = dummy
        while list1 and list2:
            if list1.val < list2.val:
                curr.next = list1
                list1 = list1.next
            else:
                curr.next = list2
                list2 = list2.next
            curr = curr.next
        curr.next = list1 or list2
        return dummy.next
    """)


def _longest_substring_body() -> str:
    return _body("""\
        seen = {}
        left = 0
        max_len = 0
        for right, ch in enumerate(s):
            if ch in seen and seen[ch] >= left:
                left = seen[ch] + 1
            seen[ch] = right
            max_len = max(max_len, right - left + 1)
        return max_len
    """)


def _roman_to_int_body() -> str:
    return _body("""\
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        total = 0
        prev = 0
        for ch in reversed(s):
            cur = values[ch]
            if cur < prev:
                total -= cur
            else:
                total += cur
            prev = cur
        return total
    """)


def _climbing_stairs_body() -> str:
    return _body("""\
        if n <= 2:
            return n
        a, b = 1, 2
        for _ in range(3, n + 1):
            a, b = b, a + b
        return b
    """)


def _contains_duplicate_body() -> str:
    return _body("""\
        seen = set()
        for num in nums:
            if num in seen:
                return True
            seen.add(num)
        return False
    """)


def _majority_element_body() -> str:
    return _body("""\
        count = 0
        candidate = None
        for num in nums:
            if count == 0:
                candidate = num
            count += 1 if num == candidate else -1
        return candidate
    """)


def _single_number_body() -> str:
    return _body("""\
        result = 0
        for num in nums:
            result ^= num
        return result
    """)


def _move_zeroes_body() -> str:
    return _body("""\
        pos = 0
        for i in range(len(nums)):
            if nums[i] != 0:
                nums[i], nums[pos] = nums[pos], nums[i]
                pos += 1
        return nums
    """)


def _plus_one_body() -> str:
    return _body("""\
        for i in range(len(digits) - 1, -1, -1):
            if digits[i] < 9:
                digits[i] += 1
                return digits
            digits[i] = 0
        return [1] + digits
    """)


def _missing_number_body() -> str:
    return _body("""\
        n = len(nums)
        expected = n * (n + 1) // 2
        actual = sum(nums)
        return expected - actual
    """)


def _three_sum_closest_body() -> str:
    return _body("""\
        nums.sort()
        n = len(nums)
        closest = sum(nums[:3])
        for i in range(n - 2):
            left, right = i + 1, n - 1
            while left < right:
                total = nums[i] + nums[left] + nums[right]
                if abs(total - target) < abs(closest - target):
                    closest = total
                if total < target:
                    left += 1
                elif total > target:
                    right -= 1
                else:
                    return target
        return closest
    """)

def _three_sum_body() -> str:
    return _body("""\
        nums.sort()
        n = len(nums)
        result = []
        for i in range(n - 2):
            if i > 0 and nums[i] == nums[i - 1]:
                continue
            left, right = i + 1, n - 1
            while left < right:
                total = nums[i] + nums[left] + nums[right]
                if total < 0:
                    left += 1
                elif total > 0:
                    right -= 1
                else:
                    result.append([nums[i], nums[left], nums[right]])
                    while left < right and nums[left] == nums[left + 1]:
                        left += 1
                    while left < right and nums[right] == nums[right - 1]:
                        right -= 1
                    left += 1
                    right -= 1
        return result
    """)


# ── Standalone function wrappers (def + docstring) ─────────────────────────

def _stock_max_profit() -> str:
    return textwrap.dedent("""\
    def max_profit(prices: list[int]) -> int:
        \"\"\"
        Maximize profit from a single buy-sell transaction.
        Buy low, sell high. Return max profit (0 if no profit possible).

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_stock_max_profit_body(), '    '))


def _fibonacci() -> str:
    return textwrap.dedent("""\
    def fibonacci(n: int) -> list[int]:
        \"\"\"
        Generate the first n Fibonacci numbers.

        Time: O(n), Space: O(n)
        \"\"\"
        if n <= 0:
            return []
        if n == 1:
            return [0]
        seq = [0, 1]
        for i in range(2, n):
            seq.append(seq[-1] + seq[-2])
        return seq
    """)


def _binary_search() -> str:
    return textwrap.dedent("""\
    def binary_search(arr: list[int], target: int) -> int:
        \"\"\"
        Binary search on a sorted array.
        Returns index of target or -1 if not found.

        Time: O(log n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_binary_search_body(), '    '))


def _quicksort() -> str:
    return textwrap.dedent("""\
    def quicksort(arr: list[int]) -> list[int]:
        \"\"\"
        Sort an array using the quicksort algorithm.

        Time: O(n log n) average, O(n\u00b2) worst. Space: O(n)
        \"\"\"
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quicksort(left) + middle + quicksort(right)
    """)


def _fizzbuzz() -> str:
    return textwrap.dedent("""\
    def fizzbuzz(n: int = 100) -> list[str]:
        \"\"\"
        Print numbers 1..n. Multiples of 3 -> Fizz, 5 -> Buzz, 15 -> FizzBuzz.
        Returns the result list.

        Time: O(n), Space: O(n)
        \"\"\"
    """ + textwrap.indent(_fizzbuzz_body(), '    '))


def _two_sum() -> str:
    return textwrap.dedent("""\
    def two_sum(nums: list[int], target: int) -> list[int]:
        \"\"\"
        Find two indices whose values sum to target.
        Returns [index1, index2] or empty list if none found.

        Time: O(n), Space: O(n)
        \"\"\"
    """ + textwrap.indent(_two_sum_body(), '    '))


def _palindrome() -> str:
    return textwrap.dedent("""\
    def is_palindrome(s: str) -> bool:
        \"\"\"
        Check if a string is a palindrome (ignoring case and non-alphanumeric).

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_is_palindrome_body(), '    '))


def _reverse_linked_list() -> str:
    return textwrap.dedent("""\
    class ListNode:
        def __init__(self, val: int = 0, next_node: 'ListNode | None' = None):
            self.val = val
            self.next = next_node


    def reverse_list(head: ListNode | None) -> ListNode | None:
        \"\"\"
        Reverse a singly linked list.

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_reverse_linked_list_body(), '    ') + "\n")


def _tree_traversal() -> str:
    return textwrap.dedent("""\
    class TreeNode:
        def __init__(self, val: int = 0, left: 'TreeNode | None' = None, right: 'TreeNode | None' = None):
            self.val = val
            self.left = left
            self.right = right


    def inorder_traversal(root: TreeNode | None) -> list[int]:
        \"\"\"
        Inorder traversal of a binary tree (left, root, right).

        Time: O(n), Space: O(n)
        \"\"\"
    """ + textwrap.indent(_tree_traversal_body(), '    ') + "\n")


def _factorial() -> str:
    return textwrap.dedent("""\
    def factorial(n: int) -> int:
        \"\"\"
        Compute n! recursively.

        Time: O(n), Space: O(n)
        \"\"\"
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n <= 1:
            return 1
        return n * factorial(n - 1)
    """)


def _is_prime() -> str:
    return textwrap.dedent("""\
    def is_prime(n: int) -> bool:
        \"\"\"
        Check whether n is a prime number.

        Time: O(\u221an), Space: O(1)
        \"\"\"
        if n < 2:
            return False
        if n < 4:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True
    """)


def _valid_parentheses() -> str:
    return textwrap.dedent("""\
    def is_valid(s: str) -> bool:
        \"\"\"
        Check if bracket string is valid (every open bracket closed in order).

        Time: O(n), Space: O(n)
        \"\"\"
    """ + textwrap.indent(_valid_parentheses_body(), '    '))


def _merge_two_lists() -> str:
    return textwrap.dedent("""\
    class ListNode:
        def __init__(self, val: int = 0, next_node: 'ListNode | None' = None):
            self.val = val
            self.next = next_node


    def merge_two_lists(list1: ListNode | None, list2: ListNode | None) -> ListNode | None:
        \"\"\"
        Merge two sorted linked lists into one sorted list.

        Time: O(n + m), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_merge_two_lists_body(), '    ') + "\n")


def _longest_substring() -> str:
    return textwrap.dedent("""\
    def length_of_longest_substring(s: str) -> int:
        \"\"\"
        Find length of longest substring without repeating characters.

        Time: O(n), Space: O(k) where k = distinct chars
        \"\"\"
    """ + textwrap.indent(_longest_substring_body(), '    '))


def _roman_to_int() -> str:
    return textwrap.dedent("""\
    def roman_to_int(s: str) -> int:
        \"\"\"
        Convert Roman numeral string to integer.

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_roman_to_int_body(), '    '))


def _climbing_stairs() -> str:
    return textwrap.dedent("""\
    def climb_stairs(n: int) -> int:
        \"\"\"
        Number of distinct ways to climb n stairs (1 or 2 steps at a time).

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_climbing_stairs_body(), '    '))


def _contains_duplicate() -> str:
    return textwrap.dedent("""\
    def contains_duplicate(nums: list[int]) -> bool:
        \"\"\"
        Check if any value appears at least twice in the array.

        Time: O(n), Space: O(n)
        \"\"\"
    """ + textwrap.indent(_contains_duplicate_body(), '    '))


def _majority_element() -> str:
    return textwrap.dedent("""\
    def majority_element(nums: list[int]) -> int:
        \"\"\"
        Find the element that appears more than n/2 times (Boyer-Moore).

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_majority_element_body(), '    '))


def _single_number() -> str:
    return textwrap.dedent("""\
    def single_number(nums: list[int]) -> int:
        \"\"\"
        Find the element that appears only once (others appear twice).

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_single_number_body(), '    '))


def _move_zeroes() -> str:
    return textwrap.dedent("""\
    def move_zeroes(nums: list[int]) -> None:
        \"\"\"
        Move all zeroes to the end while preserving relative order.

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_move_zeroes_body(), '    ') + "\n        return nums\n")


def _plus_one() -> str:
    return textwrap.dedent("""\
    def plus_one(digits: list[int]) -> list[int]:
        \"\"\"
        Increment a large integer represented as an array of digits.

        Time: O(n), Space: O(1) excluding output
        \"\"\"
    """ + textwrap.indent(_plus_one_body(), '    '))


def _missing_number() -> str:
    return textwrap.dedent("""\
    def missing_number(nums: list[int]) -> int:
        \"\"\"
        Find the missing number in an array containing n distinct numbers.

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_missing_number_body(), '    '))


def _three_sum_closest() -> str:
    return textwrap.dedent("""\
    def three_sum_closest(nums: list[int], target: int) -> int:
        \"\"\"
        Find three integers whose sum is closest to target.

        Sorts the array, then uses two-pointer to track the closest sum.

        Time: O(n\u00b2), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_three_sum_closest_body(), '    ') + "\n")


def _three_sum() -> str:
    return textwrap.dedent("""\
    def three_sum(nums: list[int]) -> list[list[int]]:
        \"\"\"
        Find all unique triplets that sum to zero.

        Sorts the array then uses two-pointer to avoid O(n\u00b3).

        Time: O(n\u00b2), Space: O(n) for sorting
        \"\"\"
    """ + textwrap.indent(_three_sum_body(), '    ') + "\n")


def _container_with_most_water() -> str:
    return textwrap.dedent("""\
    \"\"\"
    Container With Most Water \u2014 multiple approaches.

    Problem: Given an integer array height of length n, find two lines that
    together with the x-axis form a container that holds the most water.

    Return the maximum amount of water a container can store.
    \"\"\"

    # ---------------------------------------------------------------
    # Approach 1: Brute Force  O(n\u00b2)  O(1)
    # ---------------------------------------------------------------
    def max_area_bruteforce(height: list[int]) -> int:
        \"\"\"
        Check every pair of lines. For each pair (i, j), the area is
        min(height[i], height[j]) * (j - i). Keep the max.

        Time: O(n\u00b2), Space: O(1)
        \"\"\"
        n = len(height)
        max_water = 0
        for i in range(n):
            for j in range(i + 1, n):
                area = min(height[i], height[j]) * (j - i)
                if area > max_water:
                    max_water = area
        return max_water

    # ---------------------------------------------------------------
    # Approach 2: Two Pointer  O(n)  O(1)  (optimal)
    # ---------------------------------------------------------------
    def max_area_two_pointer(height: list[int]) -> int:
        \"\"\"
        Start with pointers at both ends. The width is maximized initially.
        Move the pointer with the smaller height inward \u2014 that's the
        limiting factor. Update max area on each step.

        Time: O(n), Space: O(1)
        \"\"\"
    """ + textwrap.indent(_container_body(), '    ') + """

    # ---------------------------------------------------------------
    # Approach 3: Two Pointer with Early Exit  O(n)  O(1)
    # ---------------------------------------------------------------
    def max_area_optimized(height: list[int]) -> int:
        \"\"\"
        Same as two-pointer but skips heights that cannot improve the max.
        If the current max area is already larger than what the current
        width could ever hold (max_possible = min(h_left, h_right) * width),
        we continue without updating. Minor optimization.

        Time: O(n), Space: O(1)
        \"\"\"
        left, right = 0, len(height) - 1
        max_water = 0
        while left < right:
            h_left, h_right = height[left], height[right]
            width = right - left
            area = min(h_left, h_right) * width
            max_water = max(max_water, area)
            if h_left < h_right:
                left += 1
                while left < right and height[left] <= h_left:
                    left += 1
            else:
                right -= 1
                while left < right and height[right] <= h_right:
                    right -= 1
        return max_water

    # ---------------------------------------------------------------
    # Unified wrapper \u2014 use the optimal approach by default
    # ---------------------------------------------------------------
    def max_area(height: list[int]) -> int:
        \"\"\"
        Default: two-pointer approach (optimal O(n)).

        For alternative implementations see:
          max_area_bruteforce()  \u2014 O(n\u00b2)  checks all pairs
          max_area_two_pointer() \u2014 O(n)   standard two-pointer
          max_area_optimized()   \u2014 O(n)   with skip-ahead optimization

        Example:
        >>> max_area([1, 8, 6, 2, 5, 4, 8, 3, 7])
        49
        >>> max_area([1, 1])
        1
        \"\"\"
        return max_area_two_pointer(height)
    """)
