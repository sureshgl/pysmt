#
# This file is part of pySMT.
#
#   Copyright 2014 Andrea Micheli and Marco Gario
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from pysmt.walkers import DagWalker


def cnf(formula, environment=None):
    """Converts the given formula in CNF represented as a formula"""
    cnfizer = CNFizer(environment)
    return cnfizer.convert_as_formula(formula)


def cnf_as_set(formula, environment=None):
    """Converts the given formula in CNF represented as a set of sets"""
    cnfizer = CNFizer(environment)
    return cnfizer.convert(formula)


class CNFizer(DagWalker):

    THEORY_PLACEHOLDER = "__Placeholder__"

    TRUE_CNF = frozenset()
    FALSE_CNF = frozenset([frozenset()])

    def __init__(self, environment=None):
        DagWalker.__init__(self, environment)
        self.mgr = self.env.formula_manager
        self._introduced_variables = {}
        self._cnf_pieces = {}

    def _key_var(self, formula):
        if formula in self._introduced_variables:
            res = self._introduced_variables[formula]
        else:
            res = self.mgr.FreshSymbol()
            self._introduced_variables[formula] = res
        return res

    def convert(self, formula):
        """Convert formula into an Equisatisfiable CNF.

        Returns a set of clauses: a set of set of literals.
        """
        tl, _cnf = self.walk(formula)
        res = [frozenset([tl])]
        for clause in _cnf:
            if len(clause) == 0:
                return CNFizer.FALSE_CNF
            simp = []
            for lit in clause:
                if lit.is_true():
                    # Prune clauses that are trivially TRUE
                    simp = None
                    break
                elif not lit.is_false():
                    # Prune FALSE literals
                    simp.append(lit)
            if simp:
                res.append(frozenset(simp))
        return frozenset(res)

    def convert_as_formula(self, formula):
        """Convert formula into an Equisatisfiable CNF.

        Returns an FNode.
        """
        lsts = self.convert(formula)

        conj = []
        for clause in lsts:
            conj.append(self.mgr.Or(clause))
        return self.mgr.And(conj)

    def printer(self, _cnf):
        print(self.serialize(_cnf))
        return

    def serialize(self, _cnf):
        clauses = []
        for clause in _cnf:
            clauses +=[" { " + " ".join(str(lit) for lit in clause) + "} "]
        res = ["{"] + clauses + ["}"]
        return "".join(res)



    def walk_forall(self, formula, args, **kwargs):
        raise NotImplementedError("CNFizer does not support quantifiers")

    def walk_exists(self, formula, args, **kwargs):
        raise NotImplementedError("CNFizer does not support quantifiers")

    def walk_and(self, formula, args, **kwargs):
        if len(args) == 1:
            return args[0]

        k = self._key_var(formula)
        _cnf = [frozenset([k] + [self.mgr.Not(a).simplify() for a,_ in args])]
        for a,c in args:
            _cnf.append(frozenset([a, self.mgr.Not(k)]))
            for clause in c:
                _cnf.append(clause)
        return k, frozenset(_cnf)

    def walk_or(self, formula, args, **kwargs):
        if len(args) == 1:
            return args[0]
        k = self._key_var(formula)
        _cnf = [frozenset([self.mgr.Not(k)] + [a for a,_ in args])]
        for a,c in args:
            _cnf.append(frozenset([k, self.mgr.Not(a)]))
            for clause in c:
                _cnf.append(clause)
        return k, frozenset(_cnf)

    def walk_not(self, formula, args, **kwargs):
        a, _cnf = args[0]
        if a.is_true():
            return self.mgr.FALSE(), CNFizer.TRUE_CNF
        elif a.is_false():
            return self.mgr.TRUE(), CNFizer.TRUE_CNF
        else:
            k = self._key_var(formula)
            return k, _cnf | frozenset([frozenset([self.mgr.Not(k),
                                                  self.mgr.Not(a).simplify()]),
                                       frozenset([k, a])])

    def walk_implies(self, formula,  args, **kwargs):
        a, cnf_a = args[0]
        b, cnf_b = args[1]

        k = self._key_var(formula)
        not_a = self.mgr.Not(a).simplify()
        not_b = self.mgr.Not(b).simplify()

        return k, (cnf_a | cnf_b | frozenset([frozenset([not_a, b, k]),
                                              frozenset([a, k]),
                                              frozenset([not_b, k])]))

    def walk_iff(self, formula, args, **kwargs):
        a, cnf_a = args[0]
        b, cnf_b = args[1]

        k = self._key_var(formula)
        not_a = self.mgr.Not(a).simplify()
        not_b = self.mgr.Not(b).simplify()
        not_k = self.mgr.Not(k)

        return k, (cnf_a | cnf_b | frozenset([frozenset([not_a, not_b, k]),
                                              frozenset([not_a, b, not_k]),
                                              frozenset([a, not_b, not_k]),
                                              frozenset([a, b, k])]))

    def walk_symbol(self, formula, **kwargs):
        if formula.is_symbol(types.BOOL):
            return formula, CNFizer.TRUE_CNF
        else:
            return CNFizer.THEORY_PLACEHOLDER

    def walk_function(self, formula, **kwargs):
        ty = formula.function_symbol().symbol_type()
        if ty.return_type.is_bool_type():
            return formula, CNFizer.TRUE_CNF
        else:
            return CNFizer.THEORY_PLACEHOLDER

    def walk_real_constant(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

    def walk_bool_constant(self, formula, **kwargs):
        if formula.is_true():
            return formula, CNFizer.TRUE_CNF
        else:
            return formula, CNFizer.TRUE_CNF

    def walk_int_constant(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

    def walk_plus(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

    def walk_minus(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

    def walk_times(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

    def walk_equals(self, formula, args, **kwargs):
        assert all(a == CNFizer.THEORY_PLACEHOLDER for a in args)
        return formula, CNFizer.TRUE_CNF

    def walk_le(self, formula, args, **kwargs):
        assert all(a == CNFizer.THEORY_PLACEHOLDER for a in args)
        return formula, CNFizer.TRUE_CNF

    def walk_lt(self, formula, args, **kwargs):
        assert all(a == CNFizer.THEORY_PLACEHOLDER for a in args), str(args)
        return formula, CNFizer.TRUE_CNF

    def walk_ite(self, formula, args, **kwargs):
        if any(a == CNFizer.THEORY_PLACEHOLDER for a in args):
            return CNFizer.THEORY_PLACEHOLDER
        else:
            (i,cnf_i),(t,cnf_t),(e,cnf_e) = args
            k = self._key_var(formula)
            not_i = self.mgr.Not(i).simplify()
            not_t = self.mgr.Not(t).simplify()
            not_e = self.mgr.Not(e).simplify()
            not_k = self.mgr.Not(k)

            return k, (cnf_i | cnf_t | cnf_e |
                       frozenset([frozenset([not_i, not_t, k]),
                                  frozenset([not_i, t, not_k]),
                                  frozenset([i, not_e, k]),
                                  frozenset([i, e, not_k])]))

    def walk_toreal(self, formula, **kwargs):
        return CNFizer.THEORY_PLACEHOLDER

#EOC CNFizer
