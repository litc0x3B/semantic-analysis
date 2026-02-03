import uuid

class KripkeScale:
    """
    Represents the ontological structure (T-Box).
    Manages concepts, relations, and their hierarchical order (ISA).
    """
    def __init__(self):
        self.concepts = {}
        self.relations = {}

    def register_concept(self, name, parents=None):
        if parents is None:
            parents = []
        c = Concept(name, parents)
        self.concepts[name] = c
        return c

    def register_relation(self, name, domain, range_concept, parents=None):
        if parents is None:
            parents = []
        r = Relation(name, domain, range_concept, parents)
        self.relations[name] = r
        return r

class Concept:
    """
    ADT: Concept. Represents a category of objects.
    """
    def __init__(self, name, parents):
        self.name = name
        self.parents = parents

    def is_a(self, other_concept):
        """Checks the transitive ISA relationship."""
        if self == other_concept:
            return True
        for parent in self.parents:
            if parent.is_a(other_concept):
                return True
        return False

    def __repr__(self):
        return f"<Concept: {self.name}>"

class Relation(Concept):
    """
    ADT: Relation. A special kind of Concept connecting two Concepts.
    """
    def __init__(self, name, domain, range_concept, parents):
        super().__init__(name, parents)
        self.domain = domain
        self.range_concept = range_concept

    def __repr__(self):
        return f"<Relation: {self.name} ({self.domain.name} -> {self.range_concept.name})>"

class Frame:
    """
    ADT: Frame. Represents an instance of a Concept (Object) or Relation (Link).
    """
    def __init__(self, concept, data=None, uid=None):
        self.uid = uid if uid else str(uuid.uuid4())[:8]
        self.concept = concept
        self.data = data if data else {}

    def is_instance_of(self, target_concept):
        """
        Checks if this frame is an instance of the target_concept (considering ISA).
        """
        return self.concept.is_a(target_concept)

    def __repr__(self):
        return f"<Frame[{self.concept.name}]: {self.uid}>"

class Link(Frame):
    """
    A specific type of Frame representing an instance of a Relation.
    """
    def __init__(self, relation, source_frame, target_frame):
        super().__init__(relation)
        self.source = source_frame
        self.target = target_frame

    def __repr__(self):
        return f"<Link[{self.concept.name}]: {self.source.uid} -> {self.target.uid}>"

class PossibleWorld:
    """
    ADT: Possible World (A-Box).
    Contains the concrete set of instances (Frames) and links.
    """
    def __init__(self, name):
        self.name = name
        self.objects = []
        self.links = []

    def add_object(self, concept, data=None, uid=None):
        obj = Frame(concept, data, uid)
        self.objects.append(obj)
        return obj

    def add_link(self, relation, source_obj, target_obj):
        # Basic validation
        if not source_obj.is_instance_of(relation.domain):
            print(f"[Warning] Source {source_obj} is not an instance of {relation.domain}")
        if not target_obj.is_instance_of(relation.range_concept):
            print(f"[Warning] Target {target_obj} is not an instance of {relation.range_concept}")
            
        link = Link(relation, source_obj, target_obj)
        self.links.append(link)
        return link

    def get_instances(self, concept):
        return [obj for obj in self.objects if obj.is_instance_of(concept)]

    def get_links(self, relation_concept):
        return [link for link in self.links if link.is_instance_of(relation_concept)]

# ==========================================
# Scenario Execution
# ==========================================

def run_scenario():
    print("=== 1-2. Initialization of Domain (University Context) ===")
    scale = KripkeScale()

    # --- 4. Describe selected system of concepts ---
    # Hierarchy:
    # Person
    #   ISA Student
    #   ISA Staff
    #       ISA Professor
    
    c_person = scale.register_concept("Person")
    c_student = scale.register_concept("Student", parents=[c_person])
    c_staff = scale.register_concept("Staff", parents=[c_person])
    c_professor = scale.register_concept("Professor", parents=[c_staff])
    
    print(f"Defined Concepts: {[c.name for c in [c_person, c_student, c_staff, c_professor]]}")

    # --- 6-7. Describe relations and ISA on relations ---
    # Relations:
    # Interact (Person -> Person)
    #   ISA Mentor (Staff -> Student)
    
    r_interact = scale.register_relation("Interact", domain=c_person, range_concept=c_person)
    r_mentor = scale.register_relation("Mentor", domain=c_staff, range_concept=c_student, parents=[r_interact])
    
    print(f"Defined Relations: {r_interact.name}, {r_mentor.name} (ISA {r_interact.name})")

    # --- 5. Define instances and check instance-of (Concept) ---
    print("\n=== 5. Working with Concept Instances ===")
    world = PossibleWorld("Semester 1")
    
    alice = world.add_object(c_student, {"name": "Alice"}, uid="Alice")
    bob = world.add_object(c_professor, {"name": "Dr. Bob"}, uid="Bob")
    
    print(f"Created instances: {alice}, {bob}")

    # Check: Is Bob a Person? (Transitive: Professor -> Staff -> Person)
    check_bob_person = bob.is_instance_of(c_person)
    print(f"Check: Is {bob.uid} instance of Person? {check_bob_person} (Expected: True)")
    
    # Check: Is Alice a Staff?
    check_alice_staff = alice.is_instance_of(c_staff)
    print(f"Check: Is {alice.uid} instance of Staff? {check_alice_staff} (Expected: False)")

    # --- 8. Create instances of relations and check instance-of (Relation) ---
    print("\n=== 8. Working with Relation Instances ===")
    
    # Bob mentors Alice
    link_mentor = world.add_link(r_mentor, bob, alice)
    print(f"Created link: {link_mentor}")
    
    # Check: Is this 'Mentor' link also an 'Interact' link? (ISA on relations)
    check_link_interact = link_mentor.is_instance_of(r_interact)
    print(f"Check: Is link instance of 'Interact'? {check_link_interact} (Expected: True)")
    
    # Negative test
    r_supervise = scale.register_relation("Supervise", c_staff, c_staff) # Dummy relation
    check_link_supervise = link_mentor.is_instance_of(r_supervise)
    print(f"Check: Is link instance of 'Supervise'? {check_link_supervise} (Expected: False)")

if __name__ == "__main__":
    run_scenario()
