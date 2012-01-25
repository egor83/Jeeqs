ace.define("ace/mode/xml", ["require", "exports", "module", "ace/lib/oop", "ace/mode/text", "ace/tokenizer", "ace/mode/xml_highlight_rules", "ace/mode/behaviour/xml", "ace/mode/folding/xml"], function (a, b, c) {
    "use strict";
    var d = a("../lib/oop"), e = a("./text").Mode, f = a("../tokenizer").Tokenizer, g = a("./xml_highlight_rules").XmlHighlightRules, h = a("./behaviour/xml").XmlBehaviour, i = a("./folding/xml").FoldMode, j = function () {
        this.$tokenizer = new f((new g).getRules()), this.$behaviour = new h, this.foldingRules = new i
    };
    d.inherits(j, e), function () {
        this.getNextLineIndent = function (a, b, c) {
            return this.$getIndent(b)
        }
    }.call(j.prototype), b.Mode = j
}), ace.define("ace/mode/xml_highlight_rules", ["require", "exports", "module", "ace/lib/oop", "ace/mode/xml_util", "ace/mode/text_highlight_rules"], function (a, b, c) {
    "use strict";
    var d = a("../lib/oop"), e = a("./xml_util"), f = a("./text_highlight_rules").TextHighlightRules, g = function () {
        this.$rules = {start:[
            {token:"text", regex:"<\\!\\[CDATA\\[", next:"cdata"},
            {token:"xml_pe", regex:"<\\?.*?\\?>"},
            {token:"comment", merge:!0, regex:"<\\!--", next:"comment"},
            {token:"meta.tag", regex:"<\\/?", next:"tag"},
            {token:"text", regex:"\\s+"},
            {token:"text", regex:"[^<]+"}
        ], cdata:[
            {token:"text", regex:"\\]\\]>", next:"start"},
            {token:"text", regex:"\\s+"},
            {token:"text", regex:"(?:[^\\]]|\\](?!\\]>))+"}
        ], comment:[
            {token:"comment", regex:".*?-->", next:"start"},
            {token:"comment", merge:!0, regex:".+"}
        ]}, e.tag(this.$rules, "tag", "start")
    };
    d.inherits(g, f), b.XmlHighlightRules = g
}), ace.define("ace/mode/xml_util", ["require", "exports", "module", "ace/lib/lang"], function (a, b, c) {
    function g(a) {
        return[
            {token:"string", regex:'".*?"'},
            {token:"string", merge:!0, regex:'["].*', next:a + "-qqstring"},
            {token:"string", regex:"'.*?'"},
            {token:"string", merge:!0, regex:"['].*", next:a + "-qstring"}
        ]
    }

    function h(a, b) {
        return[
            {token:"string", merge:!0, regex:".*?" + a, next:b},
            {token:"string", merge:!0, regex:".+"}
        ]
    }

    "use strict";
    var d = a("../lib/lang"), e = d.arrayToMap("button|form|input|label|select|textarea".split("|")), f = d.arrayToMap("table|tbody|td|tfoot|th|tr".split("|"));
    b.tag = function (a, b, c) {
        a[b] = [
            {token:"text", regex:"\\s+"},
            {token:function (a) {
                return a === "a" ? "meta.tag.anchor" : a === "img" ? "meta.tag.image" : a === "script" ? "meta.tag.script" : a === "style" ? "meta.tag.style" : e.hasOwnProperty(a.toLowerCase()) ? "meta.tag.form" : f.hasOwnProperty(a.toLowerCase()) ? "meta.tag.table" : "meta.tag"
            }, merge:!0, regex:"[-_a-zA-Z0-9:!]+", next:b + "embed-attribute-list"},
            {token:"empty", regex:"", next:b + "embed-attribute-list"}
        ], a[b + "-qstring"] = h("'", b + "embed-attribute-list"), a[b + "-qqstring"] = h('"', b + "embed-attribute-list"), a[b + "embed-attribute-list"] = [
            {token:"meta.tag", merge:!0, regex:"/?>", next:c},
            {token:"keyword.operator", regex:"="},
            {token:"entity.other.attribute-name", regex:"[-_a-zA-Z0-9:]+"},
            {token:"constant.numeric", regex:"[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?\\b"},
            {token:"text", regex:"\\s+"}
        ].concat(g(b))
    }
}), ace.define("ace/mode/behaviour/xml", ["require", "exports", "module", "ace/lib/oop", "ace/mode/behaviour", "ace/mode/behaviour/cstyle"], function (a, b, c) {
    "use strict";
    var d = a("../../lib/oop"), e = a("../behaviour").Behaviour, f = a("./cstyle").CstyleBehaviour, g = function () {
        this.inherit(f, ["string_dquotes"]), this.add("brackets", "insertion", function (a, b, c, d, e) {
            if (e == "<") {
                var f = c.getSelectionRange(), g = d.doc.getTextRange(f);
                return g !== "" ? !1 : {text:"<>", selection:[1, 1]}
            }
            if (e == ">") {
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), j = i.substring(h.column, h.column + 1);
                if (j == ">")return{text:"", selection:[1, 1]}
            } else if (e == "\n") {
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), k = i.substring(h.column, h.column + 2);
                if (k == "</") {
                    var l = this.$getIndent(d.doc.getLine(h.row)) + d.getTabString(), m = this.$getIndent(d.doc.getLine(h.row));
                    return{text:"\n" + l + "\n" + m, selection:[1, l.length, 1, l.length]}
                }
            }
        })
    };
    d.inherits(g, e), b.XmlBehaviour = g
}), ace.define("ace/mode/behaviour/cstyle", ["require", "exports", "module", "ace/lib/oop", "ace/mode/behaviour"], function (a, b, c) {
    "use strict";
    var d = a("../../lib/oop"), e = a("../behaviour").Behaviour, f = function () {
        this.add("braces", "insertion", function (a, b, c, d, e) {
            if (e == "{") {
                var f = c.getSelectionRange(), g = d.doc.getTextRange(f);
                return g !== "" ? {text:"{" + g + "}", selection:!1} : {text:"{}", selection:[1, 1]}
            }
            if (e == "}") {
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), j = i.substring(h.column, h.column + 1);
                if (j == "}") {
                    var k = d.$findOpeningBracket("}", {column:h.column + 1, row:h.row});
                    if (k !== null)return{text:"", selection:[1, 1]}
                }
            } else if (e == "\n") {
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), j = i.substring(h.column, h.column + 1);
                if (j == "}") {
                    var l = d.findMatchingBracket({row:h.row, column:h.column + 1});
                    if (!l)return null;
                    var m = this.getNextLineIndent(a, i.substring(0, i.length - 1), d.getTabString()), n = this.$getIndent(d.doc.getLine(l.row));
                    return{text:"\n" + m + "\n" + n, selection:[1, m.length, 1, m.length]}
                }
            }
        }), this.add("braces", "deletion", function (a, b, c, d, e) {
            var f = d.doc.getTextRange(e);
            if (!e.isMultiLine() && f == "{") {
                var g = d.doc.getLine(e.start.row), h = g.substring(e.end.column, e.end.column + 1);
                if (h == "}")return e.end.column++, e
            }
        }), this.add("parens", "insertion", function (a, b, c, d, e) {
            if (e == "(") {
                var f = c.getSelectionRange(), g = d.doc.getTextRange(f);
                return g !== "" ? {text:"(" + g + ")", selection:!1} : {text:"()", selection:[1, 1]}
            }
            if (e == ")") {
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), j = i.substring(h.column, h.column + 1);
                if (j == ")") {
                    var k = d.$findOpeningBracket(")", {column:h.column + 1, row:h.row});
                    if (k !== null)return{text:"", selection:[1, 1]}
                }
            }
        }), this.add("parens", "deletion", function (a, b, c, d, e) {
            var f = d.doc.getTextRange(e);
            if (!e.isMultiLine() && f == "(") {
                var g = d.doc.getLine(e.start.row), h = g.substring(e.start.column + 1, e.start.column + 2);
                if (h == ")")return e.end.column++, e
            }
        }), this.add("string_dquotes", "insertion", function (a, b, c, d, e) {
            if (e == '"') {
                var f = c.getSelectionRange(), g = d.doc.getTextRange(f);
                if (g !== "")return{text:'"' + g + '"', selection:!1};
                var h = c.getCursorPosition(), i = d.doc.getLine(h.row), j = i.substring(h.column - 1, h.column);
                if (j == "\\")return null;
                var k = d.getTokens(f.start.row, f.start.row)[0].tokens, l = 0, m, n = -1;
                for (var o = 0; o < k.length; o++) {
                    m = k[o], m.type == "string" ? n = -1 : n < 0 && (n = m.value.indexOf('"'));
                    if (m.value.length + l > f.start.column)break;
                    l += k[o].value.length
                }
                if (!m || n < 0 && m.type !== "comment" && (m.type !== "string" || f.start.column !== m.value.length + l - 1 && m.value.lastIndexOf('"') === m.value.length - 1))return{text:'""', selection:[1, 1]};
                if (m && m.type === "string") {
                    var p = i.substring(h.column, h.column + 1);
                    if (p == '"')return{text:"", selection:[1, 1]}
                }
            }
        }), this.add("string_dquotes", "deletion", function (a, b, c, d, e) {
            var f = d.doc.getTextRange(e);
            if (!e.isMultiLine() && f == '"') {
                var g = d.doc.getLine(e.start.row), h = g.substring(e.start.column + 1, e.start.column + 2);
                if (h == '"')return e.end.column++, e
            }
        })
    };
    d.inherits(f, e), b.CstyleBehaviour = f
}), ace.define("ace/mode/folding/xml", ["require", "exports", "module", "ace/lib/oop", "ace/lib/lang", "ace/range", "ace/mode/folding/fold_mode", "ace/token_iterator"], function (a, b, c) {
    "use strict";
    var d = a("../../lib/oop"), e = a("../../lib/lang"), f = a("../../range").Range, g = a("./fold_mode").FoldMode, h = a("../../token_iterator").TokenIterator, i = b.FoldMode = function (a) {
        g.call(this), this.voidElements = a || {}
    };
    d.inherits(i, g), function () {
        this.getFoldWidget = function (a, b, c) {
            var d = this._getFirstTagInLine(a, c);
            return d.closing ? b == "markbeginend" ? "end" : "" : !d.tagName || this.voidElements[d.tagName.toLowerCase()] ? "" : d.selfClosing ? "" : d.value.indexOf("/" + d.tagName) !== -1 ? "" : "start"
        }, this._getFirstTagInLine = function (a, b) {
            var c = a.getTokens(b, b)[0].tokens, d = "";
            for (var f = 0; f < c.length; f++) {
                var g = c[f];
                g.type.indexOf("meta.tag") === 0 ? d += g.value : d += e.stringRepeat(" ", g.value.length)
            }
            return this._parseTag(d)
        }, this.tagRe = /^(\s*)(<?(\/?)([-_a-zA-Z0-9:!]*)\s*(\/?)>?)/, this._parseTag = function (a) {
            var b = this.tagRe.exec(a), c = this.tagRe.lastIndex || 0;
            return this.tagRe.lastIndex = 0, {value:a, match:b ? b[2] : "", closing:b ? !!b[3] : !1, selfClosing:b ? !!b[5] || b[2] == "/>" : !1, tagName:b ? b[4] : "", column:b[1] ? c + b[1].length : c}
        }, this._readTagForward = function (a) {
            var b = a.getCurrentToken();
            if (!b)return null;
            var c = "", d;
            do if (b.type.indexOf("meta.tag") === 0) {
                if (!d)var d = {row:a.getCurrentTokenRow(), column:a.getCurrentTokenColumn()};
                c += b.value;
                if (c.indexOf(">") !== -1) {
                    var e = this._parseTag(c);
                    return e.start = d, e.end = {row:a.getCurrentTokenRow(), column:a.getCurrentTokenColumn() + b.value.length}, a.stepForward(), e
                }
            } while (b = a.stepForward());
            return null
        }, this._readTagBackward = function (a) {
            var b = a.getCurrentToken();
            if (!b)return null;
            var c = "", d;
            do if (b.type.indexOf("meta.tag") === 0) {
                d || (d = {row:a.getCurrentTokenRow(), column:a.getCurrentTokenColumn() + b.value.length}), c = b.value + c;
                if (c.indexOf("<") !== -1) {
                    var e = this._parseTag(c);
                    return e.end = d, e.start = {row:a.getCurrentTokenRow(), column:a.getCurrentTokenColumn()}, a.stepBackward(), e
                }
            } while (b = a.stepBackward());
            return null
        }, this._pop = function (a, b) {
            while (a.length) {
                var c = a[a.length - 1];
                if (!b || c.tagName == b.tagName)return a.pop();
                if (this.voidElements[b.tagName])return;
                if (this.voidElements[c.tagName]) {
                    a.pop();
                    continue
                }
                return null
            }
        }, this.getFoldWidgetRange = function (a, b, c) {
            var d = this._getFirstTagInLine(a, c);
            if (!d.match)return null;
            var e = d.closing || d.selfClosing, g = [], i;
            if (!e) {
                var j = new h(a, c, d.column), k = {row:c, column:d.column + d.tagName.length + 2};
                while (i = this._readTagForward(j)) {
                    if (i.selfClosing) {
                        if (!g.length)return i.start.column += i.tagName.length + 2, i.end.column -= 2, f.fromPoints(i.start, i.end);
                        continue
                    }
                    if (i.closing) {
                        this._pop(g, i);
                        if (g.length == 0)return f.fromPoints(k, i.start)
                    } else g.push(i)
                }
            } else {
                var j = new h(a, c, d.column + d.match.length), l = {row:c, column:d.column};
                while (i = this._readTagBackward(j)) {
                    if (i.selfClosing) {
                        if (!g.length)return i.start.column += i.tagName.length + 2, i.end.column -= 2, f.fromPoints(i.start, i.end);
                        continue
                    }
                    if (!i.closing) {
                        this._pop(g, i);
                        if (g.length == 0)return i.start.column += i.tagName.length + 2, f.fromPoints(i.start, l)
                    } else g.push(i)
                }
            }
        }
    }.call(i.prototype)
}), ace.define("ace/mode/folding/fold_mode", ["require", "exports", "module", "ace/range"], function (a, b, c) {
    "use strict";
    var d = a("../../range").Range, e = b.FoldMode = function () {
    };
    ((function () {
        this.foldingStartMarker = null, this.foldingStopMarker = null, this.getFoldWidget = function (a, b, c) {
            var d = a.getLine(c);
            return this.foldingStartMarker.test(d) ? "start" : b == "markbeginend" && this.foldingStopMarker && this.foldingStopMarker.test(d) ? "end" : ""
        }, this.getFoldWidgetRange = function (a, b, c) {
            return null
        }, this.indentationBlock = function (a, b, c) {
            var e = /^\s*/, f = b, g = b, h = a.getLine(b), i = c || h.length, j = h.match(e)[0].length, k = a.getLength();
            while (++b < k) {
                h = a.getLine(b);
                var l = h.match(e)[0].length;
                if (l == h.length)continue;
                if (l <= j)break;
                g = b
            }
            if (g > f) {
                var m = a.getLine(g).length;
                return new d(f, i, g, m)
            }
        }, this.openingBracketBlock = function (a, b, c, e) {
            var f = {row:c, column:e + 1}, g = a.$findClosingBracket(b, f);
            if (!g)return;
            var h = a.foldWidgets[g.row];
            return h == null && (h = this.getFoldWidget(a, g.row)), h == "start" && (g.row--, g.column = a.getLine(g.row).length), d.fromPoints(f, g)
        }
    })).call(e.prototype)
}), function () {
    ace.require(["ace/ace"], function (a) {
        window.ace || (window.ace = {});
        for (var b in a)a.hasOwnProperty(b) && (ace[b] = a[b])
    })
}()