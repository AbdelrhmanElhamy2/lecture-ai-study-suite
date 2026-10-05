import re

def test_formatter(text):
    text = text.replace('\x0c', 'f').replace('\x08', 'b')
    text = text.replace('\x09ext', r'\text').replace('\x09imes', r'\times')
    text = text.replace('\x09heta', r'\theta').replace('\x09hickapprox', r'\approx')
    text = text.replace('\x09o', r'\to').replace('\x09au', r'\tau')

    # Ensure \text{, \frac{, \sqrt{ have leading backslash
    text = re.sub(r'(?<!\\)frac\{', r'\\frac{', text)
    text = re.sub(r'(?<!\\)text\{', r'\\text{', text)
    text = re.sub(r'(?<!\\)sqrt\{', r'\\sqrt{', text)
    
    # 2. \left and \right delimiters (MUST be before \le)
    text = re.sub(r'\\left\s*\(', '(', text)
    text = re.sub(r'\\right\s*\)', ')', text)
    text = re.sub(r'\\left\s*\[', '[', text)
    text = re.sub(r'\\right\s*\]', ']', text)
    text = re.sub(r'\\left\s*\\?\{', '{', text)
    text = re.sub(r'\\right\s*\\?\}', '}', text)
    text = re.sub(r'\\left\s*\|', '|', text)
    text = re.sub(r'\\right\s*\|', '|', text)
    text = re.sub(r'\\left\.', '', text)
    text = re.sub(r'\\right\.', '', text)
    text = re.sub(r'\\left(?![a-zA-Z])', '', text)
    text = re.sub(r'\\right(?![a-zA-Z])', '', text)

    # 3. Text and style wrappers: convert \text{...} to plain text
    text = re.sub(r'\\?text\{([^{}]+)\}', r' \1 ', text)
    text = re.sub(r'\\?mathrm\{([^{}]+)\}', r'\1', text)
    text = re.sub(r'\\?mathbf\{([^{}]+)\}', r'<b>\1</b>', text)

    # 4. Temperatures & Degrees (^\circ\text{C}, ^\circ C, \degree, \circ)
    text = re.sub(r'\^\{\\?circ\}\s*([cCfFkK])', r'&deg;\1', text)
    text = re.sub(r'\^\\?circ\s*([cCfFkK])', r'&deg;\1', text)
    text = re.sub(r'\^\{\\?circ\}', '&deg;', text)
    text = re.sub(r'\^\\?circ', '&deg;', text)
    text = re.sub(r'\\degree', '&deg;', text)
    text = re.sub(r'\\circ', '&deg;', text)
    text = text.replace('^&deg;', '&deg;')

    # 5. Functions & Greek symbols
    math_syms = [
        (r'\\times(?![a-zA-Z])', '&times;'),
        (r'\\approx(?![a-zA-Z])', '&asymp;'),
        (r'\\thickapprox(?![a-zA-Z])', '&asymp;'),
        (r'(?<![a-zA-Z])hickapprox(?![a-zA-Z])', '&asymp;'),
        (r'\\pm(?![a-zA-Z])', '&plusmn;'),
        (r'\\mp(?![a-zA-Z])', '&minus;&plus;'),
        (r'\\le(?![a-zA-Z])', '&le;'),
        (r'\\leq(?![a-zA-Z])', '&le;'),
        (r'\\ge(?![a-zA-Z])', '&ge;'),
        (r'\\geq(?![a-zA-Z])', '&ge;'),
        (r'\\ne(?![a-zA-Z])', '&ne;'),
        (r'\\neq(?![a-zA-Z])', '&ne;'),
        (r'\\sin(?![a-zA-Z])', 'sin'),
        (r'\\cos(?![a-zA-Z])', 'cos'),
        (r'\\tan(?![a-zA-Z])', 'tan'),
        (r'\\exp(?![a-zA-Z])', 'exp'),
        (r'\\ln(?![a-zA-Z])', 'ln'),
        (r'\\log(?![a-zA-Z])', 'log'),
        (r'\\cdot(?![a-zA-Z])', '&sdot;'),
        (r'\\Delta(?![a-zA-Z])', '&Delta;'),
        (r'\\Omega(?![a-zA-Z])', '&Omega;'),
        (r'\\alpha(?![a-zA-Z])', '&alpha;'),
        (r'\\beta(?![a-zA-Z])', '&beta;'),
        (r'\\gamma(?![a-zA-Z])', '&gamma;'),
        (r'\\theta(?![a-zA-Z])', '&theta;'),
        (r'\\omega(?![a-zA-Z])', '&omega;'),
        (r'\\pi(?![a-zA-Z])', '&pi;'),
        (r'\\eta(?![a-zA-Z])', '&eta;'),
        (r'\\mu(?![a-zA-Z])', '&mu;'),
        (r'\\lambda(?![a-zA-Z])', '&lambda;'),
        (r'\\sigma(?![a-zA-Z])', '&sigma;'),
        (r'\\infty(?![a-zA-Z])', '&infin;'),
        (r'\\infin(?![a-zA-Z])', '&infin;'),
        (r'\\to(?![a-zA-Z])', '&rarr;'),
        (r'\\rightarrow(?![a-zA-Z])', '&rarr;'),
        (r'\\int(?![a-zA-Z])(?:_\{?[^{}\s]*\}?)?(?:\^\{?[^{}\s]*\}?)?', '&int;'),
    ]
    for pat, repl in math_syms:
        text = re.sub(pat, repl, text)

    # 6. Fractions
    for _ in range(3):
        text = re.sub(r'\\?frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1 / \2)', text)

    # 7. Square roots
    text = re.sub(r'\\?sqrt\{([^{}]+)\}', r'&radic;(\1)', text)

    # 8. Escape mathematical inequalities inside $...$
    def escape_inequalities(match):
        m = match.group(1)
        m = m.replace('<', '&lt;').replace('>', '&gt;')
        return f"${m}$"

    text = re.sub(r'\$([^\$]+)\$', escape_inequalities, text)
    text = re.sub(r'(?<=\s)<(?=\s|[\-0-9a-zA-Z])', '&lt;', text)
    text = re.sub(r'(?<=\s)>(?=\s|[\-0-9a-zA-Z])', '&gt;', text)

    # 9. Subscripts
    text = re.sub(r'\_\{([^{}]+)\}', r'<sub>\1</sub>', text)
    text = re.sub(r'\_([a-zA-Z0-9])', r'<sub>\1</sub>', text)

    # 10. Superscripts (including ^+, ^-, ^2, ^{...})
    text = re.sub(r'\^\{([^{}]+)\}', r'<sup>\1</sup>', text)
    text = re.sub(r'\^([\+\-]?[0-9a-zA-Z]|\+|\-)', r'<sup>\1</sup>', text)

    # 11. Format variables and expressions inside $...$
    def format_math_block(match):
        expr = match.group(1).strip()
        # Single variable before <sub>: e.g. I<sub>D</sub> -> <i>I</i><sub>D</sub>
        expr = re.sub(r'(?<![a-zA-Z0-9<i>])([IVTkqePRLvi])<sub>', r'<i>\1</i><sub>', expr)
        # Standalone variable letter: $T$, $k$, $q$, $e$, $R$ (not when preceded by number like 0 V, 5 V)
        expr = re.sub(r'(?<![0-9\.\s][0-9])(?<![a-zA-Z0-9<i>])([IVTkqePRL])(?![a-zA-Z0-9_</i>])', r'<i>\1</i>', expr)
        return expr

    text = re.sub(r'\$([^\$]+)\$', format_math_block, text)
    text = text.replace('$', '')
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = text.replace(' ( ', ' (').replace(' ) ', ') ')
    text = text.replace('( ', '(').replace(' )', ')')
    return text.strip()

with open('test_img1.txt', 'r', encoding='utf-8') as f:
    raw = f.read()

res = test_formatter(raw)
print('--- TEST RESULT ---')
print(res[:600])
print('...')
print(res[-600:])
