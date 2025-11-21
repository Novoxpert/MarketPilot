# TOON Usage Guide (Python)  

This guide explains how to use the [toon-python](https://github.com/toon-format/toon-python) library in this repository to encode and decode data using the TOON format.

![Token-Oriented Object Notation (TOON)](https://github.com/toon-format/toon/blob/main/.github/og.png?raw=true)

---

## What is TOON?

TOON (Token-Oriented Object Notation) is a compact, human-readable serialization format designed to reduce token usage in large language model (LLM) contexts. It combines YAML-style indentation with CSV-style tabular arrays to represent data very efficiently. :contentReference[oaicite:0]{index=0}  

With the Python implementation (`toon-python`), you can:  
- **Encode** Python objects into TOON-formatted strings  
- **Decode** TOON strings back into Python objects  
- Measure token savings compared to JSON  
- Use a CLI for encoding/decoding files  

---

## Quick Start (Python API)

```python
from toon_format import encode, decode

# Simple object
data = {"name": "Alice", "age": 30}
toon_str = encode(data)
print(toon_str)
# Output:
# name: Alice
# age: 30

# Tabular array (uniform objects)
users = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
]
toon_table = encode(users)
print(toon_table)
# Output something like:
# [2,]{id,name}:
#   1,Alice
#   2,Bob

# Decode a TOON string back into Python data
parsed = decode("items[2]: apple,banana")
print(parsed)  # {'items': ['apple', 'banana']}
```

### API Options

* `encode(value, options=None)` → `str`

  * `delimiter`: default `","`, but you can use `"\t"` or `"|"`
  * `indent`: number of spaces (default `2`)
  * `lengthMarker`: by default `""`; set to `"#"` to prefix array lengths

* `decode(input_str, options=None)` → Python object

  * `indent`: expected indent size (default `2`)
  * `strict`: whether to validate syntax / lengths / delimiters (default `True`)

---

## Token Counting & Comparison

You can also estimate how many tokens you save by using TOON vs JSON:

```python
from toon_format import estimate_savings, compare_formats, count_tokens

data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

result = estimate_savings(data)
print(f"Saves {result['savings_percent']:.1f}% tokens")

# Visual format comparison:
print(compare_formats(data))

# Count tokens of a TOON string:
toon_str = encode(data)
tokens = count_tokens(toon_str)
print("TOON token count:", tokens)
```

> ⚠️ Note: For token counting, you need `tiktoken` installed (or similar) as a dependency. ([GitHub][1])

---

## CLI Usage

The library provides a command-line tool `toon` (if installed) for converting files or stdin/stdout:

```bash
# Encode a JSON file to TOON
toon input.json -o output.toon

# Decode a TOON file back to JSON
toon data.toon -o output.json

# Use stdin/stdout
echo '{"x": 1}' | toon -

# CLI options (examples):
toon data.json --encode --delimiter "\t" --length-marker
toon data.toon --decode --no-strict --indent 4
```

Key CLI options:

* `-e, --encode` — encode input to TOON
* `-d, --decode` — decode TOON input
* `-o, --output` — specify output file
* `--delimiter` — set custom delimiter (e.g. tab)
* `--indent` — number of spaces for indentation
* `--length-marker` — whether to prefix length (e.g. `#`)
* `--no-strict` — turn off strict validation

---

## When to Use TOON

* When you have **uniform tabular data** (list of dicts with the same keys), since TOON can represent them very compactly. ([GitHub][2])
* When you're sending structured data into LLMs and **token cost matters**.
* When you want a human-readable serialization (better than pure JSON for nested data).

**When not to use TOON**:

* Deeply nested or highly heterogeneous data, where JSON might be more efficient or simpler. ([GitHub][2])
* If your tooling or downstream pipeline *requires* JSON and doesn’t support TOON.


[1]: https://github.com/toon-format/toon-python?utm_source=chatgpt.com "GitHub - toon-format/toon-python: 🐍 Community-driven Python implementation of TOON"
[2]: https://github.com/toon-format/toon?utm_source=chatgpt.com "GitHub - toon-format/toon: 🎒 Token-Oriented Object Notation (TOON) – Compact, human-readable, schema-aware JSON for LLM prompts. Spec, benchmarks, TypeScript SDK."
[3]: https://github.com/toon-format/toon-python "GitHub - toon-format/toon-python:  Community-driven Python implementation of TOON"
