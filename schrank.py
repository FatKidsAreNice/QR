class Schrank:
    """Eine einfache Klasse, die einen Schrank repräsentiert."""
    def __init__(self, ware, erscheinungspunkt, abgangspunkt):
        self.ware = ware
        self.erscheinungspunkt = erscheinungspunkt
        self.abgangspunkt = abgangspunkt

    def __repr__(self):
        # Eine nützliche "repr"-Methode, um das Objekt schön auszugeben
        return f"<Schrank(ware='{self.ware}', von='{self.erscheinungspunkt}')>"