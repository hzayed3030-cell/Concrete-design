"""
ECP 203 Engineering Dashboard - Floating Calculator & Inline Expression Evaluator
================================================================================
Provides:
1. Modeless draggable engineering calculator with full math engine (arithmetic, powers, roots, trig, constants).
2. Inline expression evaluation for all numeric input fields in the application (1.4*150 + 1.6*90 -> 354).
3. Zero-eval, AST/Shunting-Yard safe parser (strictly no eval() or Function() calls).
4. Fixed floating action button (FAB) at bottom-right corner.
5. Quick Click-to-Copy and Insert-into-Active-Input bridges.
6. Full keyboard shortcuts: F2 / Ctrl+Shift+C (toggle), Esc (close), Numpad / math keys.
"""

import streamlit as st
import streamlit.components.v1 as components

CALCULATOR_INJECTION_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { margin: 0; padding: 0; overflow: hidden; background: transparent; }
  </style>
</head>
<body>
<script>
(function() {
  var parentDoc = null;
  var parentWin = null;
  try {
    if (window.parent && window.parent.document) {
      parentDoc = window.parent.document;
      parentWin = window.parent;
    } else {
      parentDoc = document;
      parentWin = window;
    }
  } catch(e) {
    parentDoc = document;
    parentWin = window;
  }

  // ==========================================================================
  // 1. SAFE MATH PARSER & EVALUATOR (Shunting-Yard Dijkstra Algorithm)
  // Strictly ZERO eval() or Function() calls. Safe, fast & deterministic.
  // ==========================================================================
  var SafeMath = (function() {
    var angleMode = 'DEG'; // 'DEG' or 'RAD'

    var CONSTANTS = {
      'pi': Math.PI,
      'PI': Math.PI,
      'e': Math.E,
      'E': Math.E
    };

    function toRadians(val) {
      return angleMode === 'DEG' ? (val * Math.PI) / 180 : val;
    }

    var FUNCTIONS = {
      'sqrt': function(a) { if (a < 0) throw new Error("Negative sqrt"); return Math.sqrt(a); },
      'sin': function(a) {
        var rad = toRadians(a);
        var res = Math.sin(rad);
        return Math.abs(res) < 1e-12 ? 0 : res;
      },
      'cos': function(a) {
        var rad = toRadians(a);
        var res = Math.cos(rad);
        return Math.abs(res) < 1e-12 ? 0 : res;
      },
      'tan': function(a) {
        var rad = toRadians(a);
        if (Math.abs(Math.cos(rad)) < 1e-12) throw new Error("Tan undefined");
        return Math.tan(rad);
      },
      'abs': function(a) { return Math.abs(a); },
      'log': function(a) { if (a <= 0) throw new Error("Log <= 0"); return Math.log10(a); },
      'ln': function(a) { if (a <= 0) throw new Error("Ln <= 0"); return Math.log(a); },
      'inv': function(a) { if (Math.abs(a) < 1e-15) throw new Error("Div by 0"); return 1 / a; },
      'sqr': function(a) { return a * a; }
    };

    var OPERATORS = {
      '^': { prec: 4, assoc: 'right', unary: false },
      'u-': { prec: 3, assoc: 'right', unary: true },
      '*': { prec: 2, assoc: 'left', unary: false },
      '/': { prec: 2, assoc: 'left', unary: false },
      '%': { prec: 2, assoc: 'left', unary: false },
      '+': { prec: 1, assoc: 'left', unary: false },
      '-': { prec: 1, assoc: 'left', unary: false }
    };

    function tokenize(expr) {
      var tokens = [];
      var str = expr.replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-').trim();
      var i = 0;
      var len = str.length;

      while (i < len) {
        var c = str[i];

        if (/\\s/.test(c)) {
          i++;
          continue;
        }

        // Numbers (integers, decimals, scientific notation)
        if (/[0-9]/.test(c) || (c === '.' && i + 1 < len && /[0-9]/.test(str[i + 1]))) {
          var numStr = '';
          var hasDot = false;
          while (i < len && (/[0-9]/.test(str[i]) || (str[i] === '.' && !hasDot))) {
            if (str[i] === '.') hasDot = true;
            numStr += str[i];
            i++;
          }
          if (i < len && (str[i] === 'e' || str[i] === 'E')) {
            var expStr = str[i];
            i++;
            if (i < len && (str[i] === '+' || str[i] === '-')) {
              expStr += str[i];
              i++;
            }
            while (i < len && /[0-9]/.test(str[i])) {
              expStr += str[i];
              i++;
            }
            numStr += expStr;
          }
          var parsedNum = parseFloat(numStr);
          if (isNaN(parsedNum)) throw new Error("Invalid number: " + numStr);
          tokens.push({ type: 'NUM', val: parsedNum });
          continue;
        }

        // Functions or identifiers
        if (/[a-zA-Z_]/.test(c)) {
          var ident = '';
          while (i < len && /[a-zA-Z0-9_]/.test(str[i])) {
            ident += str[i];
            i++;
          }
          var lowerIdent = ident.toLowerCase();
          if (CONSTANTS.hasOwnProperty(ident) || CONSTANTS.hasOwnProperty(lowerIdent)) {
            var cVal = CONSTANTS.hasOwnProperty(ident) ? CONSTANTS[ident] : CONSTANTS[lowerIdent];
            tokens.push({ type: 'NUM', val: cVal });
          } else if (FUNCTIONS.hasOwnProperty(lowerIdent)) {
            tokens.push({ type: 'FUNC', val: lowerIdent });
          } else if (ident === 'x' || ident === 'X') {
            var prev = tokens[tokens.length - 1];
            if (prev && (prev.type === 'NUM' || prev.type === 'RPAREN')) {
              tokens.push({ type: 'OP', val: '*' });
            } else {
              throw new Error("Unknown variable: " + ident);
            }
          } else {
            throw new Error("Unknown symbol: " + ident);
          }
          continue;
        }

        // Power operator **
        if (c === '*' && i + 1 < len && str[i + 1] === '*') {
          tokens.push({ type: 'OP', val: '^' });
          i += 2;
          continue;
        }

        // Parentheses
        if (c === '(') {
          tokens.push({ type: 'LPAREN', val: '(' });
          i++;
          continue;
        }
        if (c === ')') {
          tokens.push({ type: 'RPAREN', val: ')' });
          i++;
          continue;
        }

        // Operators & Unary Minus
        if (c === '+' || c === '-' || c === '*' || c === '/' || c === '^' || c === '%') {
          if (c === '-') {
            var prevToken = tokens[tokens.length - 1];
            if (!prevToken || prevToken.type === 'OP' || prevToken.type === 'LPAREN') {
              tokens.push({ type: 'OP', val: 'u-' });
              i++;
              continue;
            }
          }
          tokens.push({ type: 'OP', val: c });
          i++;
          continue;
        }

        // Square root symbol √
        if (c === '√') {
          tokens.push({ type: 'FUNC', val: 'sqrt' });
          i++;
          continue;
        }

        throw new Error("Unexpected character: " + c);
      }
      return tokens;
    }

    function shuntingYard(tokens) {
      var outputQueue = [];
      var opStack = [];

      for (var j = 0; j < tokens.length; j++) {
        var token = tokens[j];

        if (token.type === 'NUM') {
          outputQueue.push(token);
        } else if (token.type === 'FUNC') {
          opStack.push(token);
        } else if (token.type === 'OP') {
          var o1 = token.val;
          var op1Info = OPERATORS[o1];
          if (!op1Info) throw new Error("Unknown operator: " + o1);

          while (opStack.length > 0) {
            var top = opStack[opStack.length - 1];
            if (top.type === 'OP') {
              var o2 = top.val;
              var op2Info = OPERATORS[o2];
              if ((op1Info.assoc === 'left' && op1Info.prec <= op2Info.prec) ||
                  (op1Info.assoc === 'right' && op1Info.prec < op2Info.prec)) {
                outputQueue.push(opStack.pop());
                continue;
              }
            } else if (top.type === 'FUNC') {
              outputQueue.push(opStack.pop());
              continue;
            }
            break;
          }
          opStack.push(token);
        } else if (token.type === 'LPAREN') {
          opStack.push(token);
        } else if (token.type === 'RPAREN') {
          var foundLparen = false;
          while (opStack.length > 0) {
            var popped = opStack.pop();
            if (popped.type === 'LPAREN') {
              foundLparen = true;
              break;
            }
            outputQueue.push(popped);
          }
          if (!foundLparen) throw new Error("Mismatched parentheses");
          if (opStack.length > 0 && opStack[opStack.length - 1].type === 'FUNC') {
            outputQueue.push(opStack.pop());
          }
        }
      }

      while (opStack.length > 0) {
        var p = opStack.pop();
        if (p.type === 'LPAREN' || p.type === 'RPAREN') {
          throw new Error("Mismatched parentheses");
        }
        outputQueue.push(p);
      }

      return outputQueue;
    }

    function evaluateRPN(rpn) {
      var stack = [];
      for (var k = 0; k < rpn.length; k++) {
        var token = rpn[k];
        if (token.type === 'NUM') {
          stack.push(token.val);
        } else if (token.type === 'FUNC') {
          if (stack.length < 1) throw new Error("Missing function argument");
          var arg = stack.pop();
          var fn = FUNCTIONS[token.val];
          if (!fn) throw new Error("Unknown function: " + token.val);
          stack.push(fn(arg));
        } else if (token.type === 'OP') {
          var op = token.val;
          var opInfo = OPERATORS[op];
          if (opInfo.unary) {
            if (stack.length < 1) throw new Error("Missing unary argument");
            var uArg = stack.pop();
            if (op === 'u-') stack.push(-uArg);
          } else {
            if (stack.length < 2) throw new Error("Missing binary argument");
            var b = stack.pop();
            var a = stack.pop();
            if (op === '+') stack.push(a + b);
            else if (op === '-') stack.push(a - b);
            else if (op === '*') stack.push(a * b);
            else if (op === '/') {
              if (Math.abs(b) < 1e-15) throw new Error("Division by zero");
              stack.push(a / b);
            } else if (op === '%') {
              if (Math.abs(b) < 1e-15) throw new Error("Division by zero");
              stack.push(a % b);
            } else if (op === '^') {
              stack.push(Math.pow(a, b));
            }
          }
        }
      }

      if (stack.length !== 1) throw new Error("Invalid expression");
      var res = stack[0];
      if (typeof res !== 'number' || isNaN(res) || !isFinite(res)) {
        throw new Error("Invalid numeric result");
      }
      return res;
    }

    function evaluate(expr) {
      if (!expr || typeof expr !== 'string') return null;
      var clean = expr.trim();
      if (!clean) return null;
      var tokens = tokenize(clean);
      if (tokens.length === 0) return null;
      var rpn = shuntingYard(tokens);
      var result = evaluateRPN(rpn);
      var rounded = Math.round(result * 1e8) / 1e8;
      return rounded;
    }

    function setAngleMode(mode) {
      if (mode === 'DEG' || mode === 'RAD') {
        angleMode = mode;
      }
      return angleMode;
    }

    function getAngleMode() {
      return angleMode;
    }

    return {
      evaluate: evaluate,
      setAngleMode: setAngleMode,
      getAngleMode: getAngleMode
    };
  })();
  parentWin.SafeMath = SafeMath;

  // ==========================================================================
  // 2. REACT SYNTHETIC EVENT BRIDGE (Streamlit State Synchronization)
  // ==========================================================================
  function setNativeInputValue(element, value) {
    if (!element) return;
    try {
      var valueSetter = Object.getOwnPropertyDescriptor(element, 'value') ? Object.getOwnPropertyDescriptor(element, 'value').set : null;
      var prototype = Object.getPrototypeOf(element);
      var prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value') ? Object.getOwnPropertyDescriptor(prototype, 'value').set : null;
      if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
        prototypeValueSetter.call(element, value);
      } else if (valueSetter) {
        valueSetter.call(element, value);
      } else {
        element.value = value;
      }
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    } catch(err) {
      element.value = value;
    }
  }

  // ==========================================================================
  // 3. INLINE INPUT WATCHER (Expression Evaluator on Number Inputs)
  // ==========================================================================
  function hasMathExpression(str) {
    if (!str || typeof str !== 'string') return false;
    var trimmed = str.trim();
    // Exclude simple signed numbers like "-5" or "12.5"
    if (/^[+-]?\\d*\\.?\\d+(?:[eE][+-]?\\d+)?$/.test(trimmed)) {
      return false;
    }
    return /[+\\-*\\/×÷^%()]/.test(trimmed) || /sqrt|sin|cos|tan|pi/i.test(trimmed);
  }

  function flashFieldFeedback(el, isSuccess) {
    try {
      var origBoxShadow = el.style.boxShadow;
      var origBorderColor = el.style.borderColor;
      var origTransition = el.style.transition;

      el.style.transition = 'box-shadow 0.25s ease, border-color 0.25s ease';
      if (isSuccess) {
        el.style.borderColor = '#10b981';
        el.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.7)';
      } else {
        el.style.borderColor = '#ef4444';
        el.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.7)';
      }

      setTimeout(function() {
        el.style.borderColor = origBorderColor;
        el.style.boxShadow = origBoxShadow;
        el.style.transition = origTransition;
      }, 700);
    } catch(e) {}
  }

  function handleInputEvaluation(input) {
    if (!input || !input.value) return false;
    var rawVal = input.value;
    if (hasMathExpression(rawVal)) {
      try {
        var computed = SafeMath.evaluate(rawVal);
        if (computed !== null && !isNaN(computed) && isFinite(computed)) {
          setNativeInputValue(input, computed);
          flashFieldFeedback(input, true);
          return true;
        } else {
          // Fallback to previous valid value
          var prevVal = input.getAttribute('data-ecp-prev-val');
          if (prevVal !== null) {
            setNativeInputValue(input, prevVal);
          }
          flashFieldFeedback(input, false);
          return false;
        }
      } catch(e) {
        var prev = input.getAttribute('data-ecp-prev-val');
        if (prev !== null) {
          setNativeInputValue(input, prev);
        }
        flashFieldFeedback(input, false);
        return false;
      }
    }
    return false;
  }

  // Install document-level input listeners only once
  if (!parentWin.__ecp_inline_listeners_installed) {
    parentWin.__ecp_inline_listeners_installed = true;

    parentDoc.addEventListener('focusin', function(e) {
      var target = e.target;
      if (target && target.tagName === 'INPUT' && target.id !== 'ecp-calc-val') {
        parentWin.__ecp_last_focused_input = target;
        target.setAttribute('data-ecp-prev-val', target.value);

        if (target.type === 'number') {
          target.setAttribute('data-ecp-orig-type', 'number');
          target.type = 'text';
        }
      }
    }, true);

    parentDoc.addEventListener('keydown', function(e) {
      var target = e.target;
      if (target && target.tagName === 'INPUT' && target.id !== 'ecp-calc-val') {
        if (e.key === 'Enter') {
          if (hasMathExpression(target.value)) {
            e.preventDefault();
            e.stopPropagation();
            var success = handleInputEvaluation(target);
            if (target.getAttribute('data-ecp-orig-type') === 'number') {
              target.type = 'number';
            }
            // Trigger React update with evaluated number
            setTimeout(function() {
              target.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true
              }));
            }, 60);
          }
        }
      }
    }, true);

    parentDoc.addEventListener('focusout', function(e) {
      var target = e.target;
      if (target && target.tagName === 'INPUT' && target.id !== 'ecp-calc-val') {
        handleInputEvaluation(target);
        if (target.getAttribute('data-ecp-orig-type') === 'number') {
          target.type = 'number';
        }
      }
    }, true);
  }

  // ==========================================================================
  // 4. FLOATING ACTION BUTTON (FAB) & DRAGGABLE MODELESS WINDOW INJECTION
  // ==========================================================================
  var existingRoot = parentDoc.getElementById('ecp-floating-calc-root');
  if (existingRoot) {
    return;
  }

  var calcRoot = parentDoc.createElement('div');
  calcRoot.id = 'ecp-floating-calc-root';
  calcRoot.innerHTML = `
    <!-- INLINE STYLES FOR THE FLOATING CALCULATOR & FAB -->
    <style id="ecp-calc-custom-styles">
      #ecp-floating-calc-fab {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        border: 1.5px solid rgba(59, 130, 246, 0.6);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(59, 130, 246, 0.35);
        cursor: pointer;
        z-index: 999998;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s ease;
        outline: none;
        user-select: none;
      }
      #ecp-floating-calc-fab:hover {
        transform: scale(1.08) translateY(-2px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.55), 0 0 24px rgba(59, 130, 246, 0.6);
        border-color: #60a5fa;
      }
      #ecp-floating-calc-fab:active {
        transform: scale(0.96);
      }
      #ecp-floating-calc-fab svg {
        width: 28px;
        height: 28px;
        fill: none;
        stroke: #60a5fa;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      /* Modeless Calculator Window (NO backdrop, completely non-blocking) */
      #ecp-floating-calc-modal {
        position: fixed;
        bottom: 90px;
        right: 24px;
        width: 320px;
        background: rgba(17, 24, 39, 0.95);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1.5px solid rgba(59, 130, 246, 0.38);
        border-radius: 16px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.65), 0 0 25px rgba(59, 130, 246, 0.2);
        z-index: 999999;
        display: none;
        flex-direction: column;
        overflow: hidden;
        user-select: none;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Kufi Arabic", sans-serif;
        direction: ltr; /* Technical Calculator Grid is LTR */
        opacity: 0;
        transform: scale(0.95) translateY(10px);
        transition: opacity 0.22s ease, transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
      }

      #ecp-floating-calc-modal.ecp-open {
        display: flex;
        opacity: 1;
        transform: scale(1) translateY(0);
      }

      /* Draggable Header */
      .ecp-calc-header {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        border-bottom: 1px solid rgba(59, 130, 246, 0.25);
        padding: 8px 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: grab;
      }
      .ecp-calc-header:active {
        cursor: grabbing;
      }
      .ecp-calc-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-weight: 700;
        color: #93c5fd;
        letter-spacing: 0.2px;
      }
      .ecp-calc-title span.ecp-badge {
        font-size: 10px;
        background: rgba(59, 130, 246, 0.25);
        color: #60a5fa;
        padding: 1px 5px;
        border-radius: 4px;
        border: 1px solid rgba(59, 130, 246, 0.4);
      }
      .ecp-calc-controls {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .ecp-calc-btn-ctrl {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        color: #94a3b8;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.15s ease;
      }
      .ecp-calc-btn-ctrl:hover {
        background: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border-color: rgba(239, 68, 68, 0.4);
      }
      .ecp-calc-btn-min:hover {
        background: rgba(59, 130, 246, 0.2) !important;
        color: #93c5fd !important;
        border-color: rgba(59, 130, 246, 0.4) !important;
      }

      /* Screen Area */
      .ecp-calc-screen {
        background: #090d16;
        padding: 10px 14px 8px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        position: relative;
      }
      .ecp-calc-toast {
        position: absolute;
        top: 36px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(16, 185, 129, 0.95);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease, transform 0.2s ease;
        z-index: 10;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        white-space: nowrap;
      }
      .ecp-calc-toast.show {
        opacity: 1;
        transform: translateX(-50%) translateY(2px);
      }
      .ecp-calc-history {
        color: #64748b;
        font-size: 11px;
        font-family: monospace;
        min-height: 16px;
        word-break: break-all;
        text-align: right;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .ecp-calc-val-wrap {
        width: 100%;
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin-top: 2px;
      }
      .ecp-calc-val {
        color: #f8fafc;
        font-size: 22px;
        font-weight: 700;
        font-family: 'Consolas', 'Courier New', monospace;
        text-align: right;
        width: 100%;
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: none;
      }
      .ecp-calc-val::-webkit-scrollbar { display: none; }

      /* Action Strip */
      .ecp-calc-actions {
        display: grid;
        grid-template-columns: 1fr 1.2fr 0.9fr 0.7fr;
        gap: 5px;
        padding: 6px 10px;
        background: #0d131f;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      }
      .ecp-act-btn {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        border-radius: 6px;
        padding: 4px 6px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        transition: all 0.15s ease;
      }
      .ecp-act-btn:hover {
        background: rgba(59, 130, 246, 0.25);
        color: #ffffff;
        border-color: #60a5fa;
      }
      .ecp-act-btn:active {
        transform: scale(0.97);
      }

      /* Keypad Grid */
      .ecp-calc-keypad {
        padding: 8px 10px 10px 10px;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }
      .ecp-calc-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 5px;
      }
      .ecp-calc-row-4 {
        grid-template-columns: repeat(4, 1fr) !important;
      }

      .ecp-btn {
        background: #1e293b;
        color: #f1f5f9;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px;
        height: 33px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.12s ease;
        outline: none;
      }
      .ecp-btn:hover {
        background: #334155;
        border-color: rgba(255, 255, 255, 0.2);
      }
      .ecp-btn:active {
        transform: scale(0.94);
      }

      .ecp-btn-fn {
        background: #172033;
        color: #38bdf8;
        font-size: 11.5px;
        font-weight: 600;
        border-color: rgba(56, 189, 248, 0.2);
      }
      .ecp-btn-fn:hover {
        background: rgba(56, 189, 248, 0.2);
        color: #e0f2fe;
        border-color: #38bdf8;
      }

      .ecp-btn-op {
        background: #1e3a5f;
        color: #93c5fd;
        font-size: 14px;
        font-weight: 700;
        border-color: rgba(147, 197, 253, 0.25);
      }
      .ecp-btn-op:hover {
        background: #2563eb;
        color: #ffffff;
        border-color: #93c5fd;
      }

      .ecp-btn-clear {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.3);
      }
      .ecp-btn-clear:hover {
        background: #ef4444;
        color: #ffffff;
      }

      .ecp-btn-eq {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: #ffffff;
        font-size: 16px;
        font-weight: 700;
        border: 1px solid #34d399;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
      }
      .ecp-btn-eq:hover {
        background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.6);
      }
    </style>

    <!-- FAB BUTTON -->
    <button id="ecp-floating-calc-fab" title="آلة حاسبة هندسية (F2)">
      <svg viewBox="0 0 24 24">
        <rect x="4" y="2" width="16" height="20" rx="2"></rect>
        <line x1="8" y1="6" x2="16" y2="6"></line>
        <line x1="8" y1="10" x2="10" y2="10"></line>
        <line x1="14" y1="10" x2="16" y2="10"></line>
        <line x1="8" y1="14" x2="10" y2="14"></line>
        <line x1="14" y1="14" x2="16" y2="14"></line>
        <line x1="8" y1="18" x2="10" y2="18"></line>
        <line x1="14" y1="18" x2="16" y2="18"></line>
      </svg>
    </button>

    <!-- MODELESS DRAGGABLE WINDOW -->
    <div id="ecp-floating-calc-modal">
      <!-- HEADER -->
      <div class="ecp-calc-header" id="ecp-calc-drag-handle">
        <div class="ecp-calc-title">
          <span>🧮</span>
          <span>ECP 203 Calculator</span>
          <span class="ecp-badge">Modeless</span>
        </div>
        <div class="ecp-calc-controls">
          <button class="ecp-calc-btn-ctrl ecp-calc-btn-min" id="ecp-calc-min" title="تصغير/توسيع">_</button>
          <button class="ecp-calc-btn-ctrl" id="ecp-calc-close" title="إغلاق (Esc)">✕</button>
        </div>
      </div>

      <!-- SCREEN -->
      <div class="ecp-calc-screen">
        <div class="ecp-calc-toast" id="ecp-calc-toast">تم النسخ!</div>
        <div class="ecp-calc-history" id="ecp-calc-history"></div>
        <div class="ecp-calc-val-wrap">
          <div class="ecp-calc-val" id="ecp-calc-val">0</div>
        </div>
      </div>

      <!-- ACTION STRIP -->
      <div class="ecp-calc-actions" id="ecp-calc-actions-panel">
        <button class="ecp-act-btn" id="ecp-btn-copy" title="نسخ الناتج للحافظة">
          <span>📋</span> نسخ
        </button>
        <button class="ecp-act-btn" id="ecp-btn-insert" title="إدراج في آخر حقل نشط">
          <span>📥</span> إدراج بالحقل
        </button>
        <button class="ecp-act-btn" id="ecp-btn-deg-toggle" title="تبديل وحدة الزوايا (DEG/RAD)">
          <span>📐</span> <span id="ecp-deg-label">DEG</span>
        </button>
        <button class="ecp-act-btn ecp-btn-clear" id="ecp-btn-backspace" title="مسح الحرف الأخير">
          <span>⌫</span>
        </button>
      </div>

      <!-- KEYPAD -->
      <div class="ecp-calc-keypad" id="ecp-calc-keypad-panel">
        <!-- Row 1: Trig & Functions -->
        <div class="ecp-calc-row">
          <button class="ecp-btn ecp-btn-fn" data-action="fn" data-val="sin(">sin</button>
          <button class="ecp-btn ecp-btn-fn" data-action="fn" data-val="cos(">cos</button>
          <button class="ecp-btn ecp-btn-fn" data-action="fn" data-val="tan(">tan</button>
          <button class="ecp-btn ecp-btn-fn" data-action="fn" data-val="sqrt(">√</button>
          <button class="ecp-btn ecp-btn-fn" data-action="pow2">x²</button>
        </div>

        <!-- Row 2: Powers, Parens, Constants -->
        <div class="ecp-calc-row">
          <button class="ecp-btn ecp-btn-fn" data-action="inv">1/x</button>
          <button class="ecp-btn ecp-btn-fn" data-action="op" data-val="^">^</button>
          <button class="ecp-btn ecp-btn-fn" data-action="char" data-val="(">(</button>
          <button class="ecp-btn ecp-btn-fn" data-action="char" data-val=")">)</button>
          <button class="ecp-btn ecp-btn-fn" data-action="const" data-val="pi">π</button>
        </div>

        <!-- Row 3: Clear, %, Division -->
        <div class="ecp-calc-row ecp-calc-row-4">
          <button class="ecp-btn ecp-btn-clear" data-action="clear">C</button>
          <button class="ecp-btn ecp-btn-fn" data-action="pm">±</button>
          <button class="ecp-btn ecp-btn-op" data-action="op" data-val="%">%</button>
          <button class="ecp-btn ecp-btn-op" data-action="op" data-val="/">÷</button>
        </div>

        <!-- Row 4: 7, 8, 9, * -->
        <div class="ecp-calc-row ecp-calc-row-4">
          <button class="ecp-btn" data-action="num" data-val="7">7</button>
          <button class="ecp-btn" data-action="num" data-val="8">8</button>
          <button class="ecp-btn" data-action="num" data-val="9">9</button>
          <button class="ecp-btn ecp-btn-op" data-action="op" data-val="*">×</button>
        </div>

        <!-- Row 5: 4, 5, 6, - -->
        <div class="ecp-calc-row ecp-calc-row-4">
          <button class="ecp-btn" data-action="num" data-val="4">4</button>
          <button class="ecp-btn" data-action="num" data-val="5">5</button>
          <button class="ecp-btn" data-action="num" data-val="6">6</button>
          <button class="ecp-btn ecp-btn-op" data-action="op" data-val="-">-</button>
        </div>

        <!-- Row 6: 1, 2, 3, + -->
        <div class="ecp-calc-row ecp-calc-row-4">
          <button class="ecp-btn" data-action="num" data-val="1">1</button>
          <button class="ecp-btn" data-action="num" data-val="2">2</button>
          <button class="ecp-btn" data-action="num" data-val="3">3</button>
          <button class="ecp-btn ecp-btn-op" data-action="op" data-val="+">+</button>
        </div>

        <!-- Row 7: 0, ., = -->
        <div class="ecp-calc-row ecp-calc-row-4">
          <button class="ecp-btn" style="grid-column: span 2;" data-action="num" data-val="0">0</button>
          <button class="ecp-btn" data-action="dot">.</button>
          <button class="ecp-btn ecp-btn-eq" data-action="equals">=</button>
        </div>
      </div>
    </div>
  `;

  parentDoc.body.appendChild(calcRoot);

  // ==========================================================================
  // 5. CALCULATOR INTERACTIVITY & STATE MACHINE
  // ==========================================================================
  var fab = parentDoc.getElementById('ecp-floating-calc-fab');
  var modal = parentDoc.getElementById('ecp-floating-calc-modal');
  var dragHandle = parentDoc.getElementById('ecp-calc-drag-handle');
  var btnClose = parentDoc.getElementById('ecp-calc-close');
  var btnMin = parentDoc.getElementById('ecp-calc-min');
  var screenVal = parentDoc.getElementById('ecp-calc-val');
  var screenHistory = parentDoc.getElementById('ecp-calc-history');
  var toast = parentDoc.getElementById('ecp-calc-toast');
  var btnCopy = parentDoc.getElementById('ecp-btn-copy');
  var btnInsert = parentDoc.getElementById('ecp-btn-insert');
  var btnBackspace = parentDoc.getElementById('ecp-btn-backspace');
  var btnDegToggle = parentDoc.getElementById('ecp-btn-deg-toggle');
  var degLabel = parentDoc.getElementById('ecp-deg-label');
  var keypadPanel = parentDoc.getElementById('ecp-calc-keypad-panel');
  var actionsPanel = parentDoc.getElementById('ecp-calc-actions-panel');

  var currentExpr = '';
  var evaluatedYet = false;
  var isMinimized = false;

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(function() {
      toast.classList.remove('show');
    }, 1500);
  }

  function updateDisplay() {
    if (!currentExpr) {
      screenVal.textContent = '0';
    } else {
      var pretty = currentExpr.replace(/\\*/g, ' × ').replace(/\\//g, ' ÷ ').replace(/\\+/g, ' + ').replace(/-(?!\\d)/g, ' - ');
      screenVal.textContent = pretty;
    }
  }

  function appendText(txt) {
    if (evaluatedYet) {
      if (/[0-9.]/.test(txt)) {
        currentExpr = '';
      }
      evaluatedYet = false;
    }
    currentExpr += txt;
    updateDisplay();
  }

  function calculateResult() {
    if (!currentExpr) return;
    try {
      var res = SafeMath.evaluate(currentExpr);
      if (res !== null && !isNaN(res) && isFinite(res)) {
        screenHistory.textContent = currentExpr + ' =';
        currentExpr = res.toString();
        evaluatedYet = true;
        updateDisplay();
      } else {
        screenHistory.textContent = 'Error';
      }
    } catch(err) {
      screenHistory.textContent = 'Syntax Error';
    }
  }

  // Deg/Rad Toggle
  if (btnDegToggle) {
    btnDegToggle.addEventListener('click', function() {
      var current = SafeMath.getAngleMode();
      var next = current === 'DEG' ? 'RAD' : 'DEG';
      SafeMath.setAngleMode(next);
      if (degLabel) degLabel.textContent = next;
      showToast(next === 'DEG' ? 'الزوايا: درجات (DEG)' : 'الزوايا: راديان (RAD)');
    });
  }

  if (keypadPanel) {
    keypadPanel.addEventListener('click', function(e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      var action = btn.getAttribute('data-action');
      var val = btn.getAttribute('data-val');

      if (action === 'num') {
        appendText(val);
      } else if (action === 'op') {
        evaluatedYet = false;
        appendText(val);
      } else if (action === 'fn') {
        appendText(val);
      } else if (action === 'const') {
        appendText(val);
      } else if (action === 'char') {
        appendText(val);
      } else if (action === 'dot') {
        appendText('.');
      } else if (action === 'clear') {
        currentExpr = '';
        screenHistory.textContent = '';
        evaluatedYet = false;
        updateDisplay();
      } else if (action === 'equals') {
        calculateResult();
      } else if (action === 'pow2') {
        appendText('^2');
      } else if (action === 'inv') {
        if (currentExpr) {
          currentExpr = '1/(' + currentExpr + ')';
          calculateResult();
        }
      } else if (action === 'pm') {
        if (currentExpr) {
          if (currentExpr.startsWith('-(') && currentExpr.endsWith(')')) {
            currentExpr = currentExpr.slice(2, -1);
          } else {
            currentExpr = '-(' + currentExpr + ')';
          }
          updateDisplay();
        }
      }
    });
  }

  if (btnBackspace) {
    btnBackspace.addEventListener('click', function() {
      if (currentExpr.length > 0) {
        currentExpr = currentExpr.slice(0, -1);
        updateDisplay();
      }
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener('click', function() {
      var textToCopy = screenVal.textContent.replace(/\\s/g, '').replace(/×/g, '*').replace(/÷/g, '/');
      if (parentWin.navigator && parentWin.navigator.clipboard) {
        parentWin.navigator.clipboard.writeText(textToCopy).then(function() {
          showToast('تم النسخ!');
        }).catch(function() {
          showToast('تم النسخ!');
        });
      } else {
        showToast('تم النسخ!');
      }
    });
  }

  if (btnInsert) {
    btnInsert.addEventListener('click', function() {
      var val = screenVal.textContent.replace(/\\s/g, '').replace(/×/g, '*').replace(/÷/g, '/');
      var num = parseFloat(val);
      if (isNaN(num)) {
        showToast('لا يوجد ناتج صالح!');
        return;
      }

      var targetInput = parentWin.__ecp_last_focused_input;
      if (targetInput && parentDoc.body.contains(targetInput)) {
        setNativeInputValue(targetInput, num);
        flashFieldFeedback(targetInput, true);
        showToast('تم الإدراج في الحقل!');
      } else {
        var inputs = parentDoc.querySelectorAll('input[type="number"], [data-testid="stNumberInput"] input');
        if (inputs && inputs.length > 0) {
          var lastIn = inputs[inputs.length - 1];
          setNativeInputValue(lastIn, num);
          flashFieldFeedback(lastIn, true);
          showToast('تم الإدراج!');
        } else {
          showToast('لم يتم تحديد حقل نشط');
        }
      }
    });
  }

  if (btnMin) {
    btnMin.addEventListener('click', function() {
      isMinimized = !isMinimized;
      if (isMinimized) {
        keypadPanel.style.display = 'none';
        actionsPanel.style.display = 'none';
        btnMin.textContent = '□';
      } else {
        keypadPanel.style.display = 'flex';
        actionsPanel.style.display = 'grid';
        btnMin.textContent = '_';
      }
    });
  }

  function openCalculator() {
    modal.classList.add('ecp-open');
    parentWin.__ecp_calc_open = true;
  }

  function closeCalculator() {
    modal.classList.remove('ecp-open');
    parentWin.__ecp_calc_open = false;
  }

  function toggleCalculator() {
    if (modal.classList.contains('ecp-open')) {
      closeCalculator();
    } else {
      openCalculator();
    }
  }

  if (fab) {
    fab.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleCalculator();
    });
  }

  if (btnClose) {
    btnClose.addEventListener('click', function(e) {
      e.stopPropagation();
      closeCalculator();
    });
  }

  // Restore saved coordinates
  try {
    var savedPos = parentWin.sessionStorage.getItem('__ecp_calc_coords');
    if (savedPos) {
      var coords = JSON.parse(savedPos);
      if (coords.left && coords.top) {
        modal.style.left = coords.left + 'px';
        modal.style.top = coords.top + 'px';
        modal.style.right = 'auto';
        modal.style.bottom = 'auto';
      }
    }
  } catch(e) {}

  // ==========================================================================
  // 6. DRAGGABLE LOGIC WITH VIEWPORT BOUNDS CONSTRAINTS
  // ==========================================================================
  var isDragging = false;
  var startX = 0, startY = 0, initialLeft = 0, initialTop = 0;

  if (dragHandle) {
    dragHandle.addEventListener('mousedown', function(e) {
      if (e.target.closest('.ecp-calc-controls')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;

      var rect = modal.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;

      modal.style.left = initialLeft + 'px';
      modal.style.top = initialTop + 'px';
      modal.style.right = 'auto';
      modal.style.bottom = 'auto';

      parentDoc.body.style.userSelect = 'none';
    });
  }

  parentDoc.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    var dx = e.clientX - startX;
    var dy = e.clientY - startY;

    var newLeft = initialLeft + dx;
    var newTop = initialTop + dy;

    var maxLeft = parentWin.innerWidth - modal.offsetWidth - 8;
    var maxTop = parentWin.innerHeight - modal.offsetHeight - 8;

    newLeft = Math.max(8, Math.min(maxLeft, newLeft));
    newTop = Math.max(8, Math.min(maxTop, newTop));

    modal.style.left = newLeft + 'px';
    modal.style.top = newTop + 'px';
  });

  parentDoc.addEventListener('mouseup', function() {
    if (isDragging) {
      isDragging = false;
      parentDoc.body.style.userSelect = '';
      try {
        var rect = modal.getBoundingClientRect();
        parentWin.sessionStorage.setItem('__ecp_calc_coords', JSON.stringify({
          left: Math.round(rect.left),
          top: Math.round(rect.top)
        }));
      } catch(e) {}
    }
  });

  // ==========================================================================
  // 7. KEYBOARD SHORTCUTS (F2, Ctrl+Shift+C, Esc, Math Keypad)
  // ==========================================================================
  parentDoc.addEventListener('keydown', function(e) {
    if (e.key === 'F2' || (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c'))) {
      e.preventDefault();
      toggleCalculator();
      return;
    }

    if (e.key === 'Escape' && modal.classList.contains('ecp-open')) {
      closeCalculator();
      return;
    }

    if (modal.classList.contains('ecp-open')) {
      var isInsideModal = modal.contains(e.target);
      if (isInsideModal) {
        if (/[0-9]/.test(e.key)) {
          appendText(e.key);
          e.preventDefault();
        } else if (['+', '-', '*', '/'].indexOf(e.key) !== -1) {
          appendText(e.key);
          e.preventDefault();
        } else if (e.key === 'Enter') {
          calculateResult();
          e.preventDefault();
        } else if (e.key === 'Backspace') {
          if (currentExpr.length > 0) {
            currentExpr = currentExpr.slice(0, -1);
            updateDisplay();
          }
          e.preventDefault();
        } else if (e.key === '.' || e.key === ',') {
          appendText('.');
          e.preventDefault();
        } else if (e.key === '(' || e.key === ')') {
          appendText(e.key);
          e.preventDefault();
        }
      }
    }
  });

})();
</script>
</body>
</html>
"""


def inject_floating_calculator():
    """
    Renders the Floating Engineering Calculator & Inline Expression Evaluator
    into the application window modelessly via st.components.v1.html with 0 height.
    """
    components.html(CALCULATOR_INJECTION_HTML, height=0, width=0)
