import ast
import operator
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple, Optional, Set


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class FormulaParserVisitor(ast.NodeVisitor):
    def __init__(self, variables: Dict[str, Decimal]):
        self.variables = variables

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Num(self, node: ast.Num):  # Python < 3.8
        return Decimal(str(node.n))

    def visit_Constant(self, node: ast.Constant):  # Python >= 3.8
        if isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        raise ValueError(f"Type de constante non autorisé : {type(node.value)}")

    def visit_Name(self, node: ast.Name):
        var_name = node.id
        if var_name in self.variables:
            val = self.variables[var_name]
            if val is None:
                raise ValueError(f"Variable sans valeur : {var_name}")
            return Decimal(str(val))
        raise ValueError(f"Variable inconnue dans la formule : {var_name}")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            operand = self.visit(node.operand)
            return ALLOWED_OPERATORS[op_type](operand)
        raise ValueError(f"Opérateur unaire non autorisé : {op_type}")

    def visit_BinOp(self, node: ast.BinOp):
        op_type = type(node.op)
        if op_type in ALLOWED_OPERATORS:
            left = self.visit(node.left)
            right = self.visit(node.right)
            if op_type == ast.Div and right == Decimal("0"):
                raise ZeroDivisionError("Division par zéro")
            return ALLOWED_OPERATORS[op_type](left, right)
        raise ValueError(f"Opérateur non autorisé : {op_type}")

    def generic_visit(self, node):
        raise ValueError(f"Noeud non autorisé dans la formule : {type(node).__name__}")


def valider_formule_securisee(formule_text: str, codes_composantes_autorises: Set[str]) -> Tuple[bool, str]:
    """
    Valide une formule sans l'évaluer :
    - Syntaxe AST valide
    - Aucun noeud interdit
    - Toutes les variables utilisées doivent être dans codes_composantes_autorises
    """
    if not formule_text or not formule_text.strip():
        return False, "La formule ne peut pas être vide."

    clean_formule = formule_text.strip()
    try:
        parsed = ast.parse(clean_formule, mode="eval")
    except SyntaxError as e:
        return False, f"Erreur de syntaxe dans la formule : {e}"

    found_variables = set()

    class ValidatorVisitor(ast.NodeVisitor):
        def visit_Expression(self, node):
            self.visit(node.body)

        def visit_Num(self, node):
            pass

        def visit_Constant(self, node):
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Type de valeur non autorisé : {node.value}")

        def visit_Name(self, node):
            found_variables.add(node.id)

        def visit_UnaryOp(self, node):
            if type(node.op) not in ALLOWED_OPERATORS:
                raise ValueError(f"Opérateur unaire non autorisé : {type(node.op).__name__}")
            self.visit(node.operand)

        def visit_BinOp(self, node):
            if type(node.op) not in ALLOWED_OPERATORS:
                raise ValueError(f"Opérateur non autorisé : {type(node.op).__name__}")
            self.visit(node.left)
            self.visit(node.right)

        def generic_visit(self, node):
            raise ValueError(f"Élément non autorisé dans la formule : {type(node).__name__}")

    try:
        ValidatorVisitor().visit(parsed)
    except ValueError as err:
        return False, str(err)

    missing_vars = found_variables - set(codes_composantes_autorises)
    if missing_vars:
        return False, f"La formule contient des variables non déclarées comme composantes : {', '.join(sorted(missing_vars))}"

    return True, "Formule valide."


def evaluer_formule_securisee(formule_text: str, variables: Dict[str, Optional[Decimal]]) -> Optional[Decimal]:
    """
    Évalue de manière 100% sécurisée une formule arithmétique.
    Si une variable est None ou si division par 0 -> renvoie None.
    """
    if not formule_text or not formule_text.strip():
        return None

    # Si une des variables nécessaires vaut None, impossible d'évaluer
    for k, v in variables.items():
        if v is None:
            return None

    clean_formule = formule_text.strip()
    try:
        parsed = ast.parse(clean_formule, mode="eval")
        visitor = FormulaParserVisitor({k: Decimal(str(v)) for k, v in variables.items() if v is not None})
        result = visitor.visit(parsed)
        if isinstance(result, Decimal):
            return result
        return Decimal(str(result))
    except (ZeroDivisionError, ValueError, TypeError, InvalidOperation, SyntaxError):
        return None
