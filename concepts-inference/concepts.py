from typing import Any, Dict, Set, List, Optional, NamedTuple, Tuple
import operator


class Constraint:
    def check(self, value: Any) -> bool:
        raise NotImplementedError
    
    def implies(self, other: 'Constraint') -> bool:
        raise NotImplementedError
    
    def intersect(self, other: 'Constraint') -> 'Constraint':
        raise NotImplementedError


class IntRange(Constraint):
    def __init__(self, min_val=float('-inf'), max_val=float('inf')):
        self.min_val = min_val
        self.max_val = max_val

    def check(self, value: Any) -> bool:
        if not isinstance(value, (int, float)): return False
        return self.min_val <= value <= self.max_val

    def implies(self, other: 'Constraint') -> bool:
        if isinstance(other, IntRange):
            return self.min_val >= other.min_val and self.max_val <= other.max_val
        if isinstance(other, AnyValue):
            return True
        return False
    
    def intersect(self, other: 'Constraint') -> 'Constraint':
        if not isinstance(other, IntRange):
            raise TypeError("Cannot intersect constraints of different types")
        return IntRange(max(self.min_val, other.min_val), min(self.max_val, other.max_val))


    def __repr__(self):
        return f"[{self.min_val}..{self.max_val}]"

class ValueSet(Constraint):
    def __init__(self, allowed_values: Set[Any]):
        self.allowed = allowed_values

    def check(self, value: Any) -> bool:
        return value in self.allowed

    def implies(self, other: 'Constraint') -> bool:
        if isinstance(other, ValueSet):
            return self.allowed.issubset(other.allowed)
        if isinstance(other, AnyValue):
            return True
        return False

    def __repr__(self):
        return f"In{self.allowed}"
    
    def intersect(self, other: 'Constraint') -> 'Constraint':
        if not isinstance(other, ValueSet):
            raise TypeError("Cannot intersect constraints of different types")
        return ValueSet(self.allowed.intersection(other.allowed))

class AnyValue(Constraint):
    def check(self, value: Any) -> bool: return True
    def implies(self, other: 'Constraint') -> bool: 
        return isinstance(other, AnyValue)
    def __repr__(self): return "Any"
    def intersect(self, other: 'Constraint') -> 'Constraint':
        return other

class BaseConcept:
    def check(self, data: Any) -> bool:
        raise NotImplementedError
    
    def is_subconcept_of(self, other: 'BaseConcept') -> bool:
        raise NotImplementedError

    def __and__(self, other):
        attrs: Dict[str, AtomicConcept] = {}
        if isinstance(self, CompositeConcept):
            attrs.update(self.attributes)
        elif isinstance(self, AtomicConcept):
            attrs[self.name] = self
        
        if isinstance(other, CompositeConcept):
            for key, atom in other.attributes.items():
                if key not in attrs:
                    attrs[key] = atom
                else:
                    attrs[key] = AtomicConcept(key, attrs[key].constraint.intersect(atom.constraint))
        elif isinstance(other, AtomicConcept):
            attrs[other.name] = AtomicConcept(other.name, other.constraint.intersect(attrs[other.name].constraint))
            
        return CompositeConcept(f"({self.name}^{other.name})", attrs)

class AtomicConcept(BaseConcept):
    def __init__(self, name: str, constraint: Constraint):
        self.name = name
        self.constraint = constraint

    def check(self, data: Any) -> bool:
        return self.constraint.check(data)

    def is_subconcept_of(self, other: 'BaseConcept') -> bool:
        if isinstance(other, AtomicConcept):
            return self.name == other.name and self.constraint.implies(other.constraint)
        return False

    def __repr__(self):
        return f"Atom({self.name}: {self.constraint})"

class CompositeConcept(BaseConcept):
    def __init__(self, name: str, attributes: Dict[str, AtomicConcept]):
        self.name = name
        self.attributes = attributes

    def check(self, data_dict: Dict[str, Any]) -> bool:
        if not isinstance(data_dict, dict): return False
        for attr_name, atom in self.attributes.items():
            if attr_name not in data_dict: return False
            if not atom.check(data_dict[attr_name]): return False
        return True

    def is_subconcept_of(self, other: 'BaseConcept') -> bool:
        if isinstance(other, AtomicConcept): 
            return len(self.attributes) == 1 and \
                   other.name in self.attributes \
                   and self.attributes[other.name].constraint.implies(other.constraint)
        
                
        if isinstance(other, CompositeConcept):
            for key, other_atom in other.attributes.items():
                if key not in self.attributes: return False
                if not self.attributes[key].constraint.implies(other_atom.constraint): return False
            return True
        return False

    def __repr__(self):
        return f"Concept[{self.name}]"

class LinkFrame:
    def __init__(self, name: str, source_type: BaseConcept, dest_type: BaseConcept):
        self.name = name
        self.source_type = source_type
        self.dest_type = dest_type

    def is_subframe_of(self, other: 'LinkFrame') -> bool:
        return (self.source_type.is_subconcept_of(other.source_type) and 
                self.dest_type.is_subconcept_of(other.dest_type))

    def __repr__(self):
        return f"RelType<{self.name}>"

class PossibleWorld:
    def __init__(self, name):
        self.name = name
        self.concepts: Dict[str, Dict[str, Any]] = {} # uid to data_dict
        self.frames: Dict[str, Frame] = {}

    def add_concept(self, name, data: Dict[str, Any]) -> 'PossibleWorld':
        self.concepts[name] = data
        return self
    
    def get_concept(self, uid: str) -> Dict[str, Any]:
        return self.concepts.get(uid)

    def get_extension(self, concept: BaseConcept) -> List[Tuple[str, Dict[str, Any]]]:
        return [(uid, data) for uid, data in self.concepts.items() if concept.check(data)]

    def __repr__(self):
        return f"World<{self.name}>"

class KripkeStructure:
    def __init__(self):
        self.worlds = {}
        self.accessibility = {}

    def add_world(self, world: PossibleWorld):
        self.worlds[world.name] = world

    def add_access(self, from_world, to_world):
        if from_world not in self.accessibility: self.accessibility[from_world] = []
        self.accessibility[from_world].append(to_world)

    def get_reachable_extension(self, start_world_name: str, concept: BaseConcept) -> Dict[str, List[str]]:
        visited = set()
        queue = [start_world_name]
        results = {}

        while queue:
            current_name = queue.pop(0)
            if current_name in visited:
                continue
            visited.add(current_name)
            
            world = self.worlds.get(current_name)
            if world:
                extension = world.get_extension(concept)
                if extension:
                    results[current_name] = extension
            
            neighbors = self.accessibility.get(current_name, [])
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append(neighbor)
        
        return results

class FrameArgInfo(NamedTuple):
    name: str
    role: str
    type: BaseConcept
    

class Frame:
    def __init__(self, name: str, argsInfo: List[FrameArgInfo]):
        self.name = name
        self.argsInfo = dict([(x.name, x) for x in argsInfo])
        self._intersection = set([self])

    def __and__(self, other: 'Frame'):
        self.intersect(other, f"({self.name}^{other.name})")
        
    
    def intersect(self, other: 'Frame', name: str):
        argInfos = self.argsInfo.copy() 
        argInfos.update([(k, v) for k, v in other.argsInfo.items() if k not in self.argsInfo.keys()])
        sameNames = [(k, v) for k, v in other.argsInfo.items() if k in self.argsInfo.keys()]
        for _, info in sameNames:
            if self.argsInfo[info.name].role != info.role:
                raise ValueError(f"Cannot intersect concepts: concepts depend on variable with the same name but different roles")
            argInfos[info.name] = FrameArgInfo(type=info.type & self.argsInfo[info.name].type, name=info.name, role=info.role)

        res = Frame(name, list(argInfos.values()))
        res._intersection = self._intersection.union(other._intersection)
        return res
    
    def is_subframe_of(self, other: 'Frame') -> bool:
        return other._intersection.issubset(self._intersection)
    
    def __repr__(self):
        return f"Frame[{self.name}]"


class FrameInstance:
    def __init__(self, frame: Frame, world: PossibleWorld, args: Dict[str, Dict[str, Any]]):
        self.frame = frame
        self.world = world
        self.args = args
        self.conceptInstances: Dict[str, Dict[str, Any]] = dict(map(lambda x: (x.value, self.world.concepts[x.value]), args))
        for var_name, concept in self.conceptInstances.items():
            if not self.frame.argsInfo[var_name].type.check(concept):
                raise ValueError(f"Type mismatch: concept is not of subtype {self.frame.argsInfo[var_name].type}")

    def __repr__(self):
        return f"FrameInstance[{self.frame.name}]"
    
    def is_instance_of(self, target_frame: Frame) -> bool:
        return self.frame.is_subframe_of(target_frame)


class LinkFrameInstance:
    def __init__(self, relation_type: LinkFrame, world: PossibleWorld, source_uid: str, target_uid: str):
        self.relation_type = relation_type
        self.world = world
        self.source = source_uid
        self.target = target_uid
        self._validate()

    def _validate(self):
        src_data = self.world.concepts.get(self.source)
        tgt_data = self.world.concepts.get(self.target)
        
        if not src_data: raise ValueError(f"Source {self.source} not found.")
        if not tgt_data: raise ValueError(f"Target {self.target} not found.")
        
        if not self.relation_type.source_type.check(src_data):
            raise ValueError(f"Source {self.source} does not satisfy source_type {self.relation_type.source_type.name}")
        if not self.relation_type.dest_type.check(tgt_data):
            raise ValueError(f"Target {self.target} does not satisfy dest_type {self.relation_type.dest_type.name}")

    def is_instance_of(self, target_rel_type: LinkFrame) -> bool:
        if self.relation_type == target_rel_type: return True
        return self.relation_type.is_subframe_of(target_rel_type)

    def __repr__(self):
        return f"Frame[{self.relation_type.name}]({self.source} -> {self.target})"

def run_scenario():
    print("\n" + "="*50)
    print("TASK 1 & 4: Define Domain & Concepts")
    print("Domain: IoT Smart Home")
    print("="*50)
    
    # Attributes
    atom_proto_any = AtomicConcept("protocol", ValueSet({"WiFi", "ZigBee"}))
    atom_proto_zig = AtomicConcept("protocol", ValueSet({"ZigBee"}))
    atom_bat_any   = AtomicConcept("battery", IntRange(0, 100))
    atom_bat_full  = AtomicConcept("battery", IntRange(80, 100))
    atom_role_dev  = AtomicConcept("role", ValueSet({"Sensor", "Hub"}))
    atom_role_sen  = AtomicConcept("role", ValueSet({"Sensor"}))
    atom_role_hub  = AtomicConcept("role", ValueSet({"Hub"}))

    # Concepts
    c_wireless_device = atom_proto_any & atom_bat_any & atom_role_dev
    c_wireless_device.name = "WirelessDevice"
    
    c_sensor = atom_proto_zig & atom_bat_any & atom_role_sen
    c_sensor.name = "Sensor"

    c_rel_sensor = c_sensor & atom_bat_full
    c_rel_sensor.name = "ReliableSensor"
    
    c_hub = c_wireless_device & atom_role_hub
    c_hub.name = "Hub"

    c_wired_hub = atom_role_hub & atom_proto_any
    c_wired_hub.name = "WiredHub"

    print(f"[Defined] {c_wireless_device.name}")
    print(f"[Defined] {c_sensor.name}")
    print(f"[Defined] {c_rel_sensor.name}")
    print(f"[Defined] {c_hub.name}")
    print(f"[Defined] {c_wired_hub.name}")


    print("\n" + "="*50)
    print("TASK 5: Concept ISA & Instances")
    print("="*50)

    # Check ISA
    print(f"[Check] ReliableSensor ISA Sensor? {c_rel_sensor.is_subconcept_of(c_sensor)} (True: Constraints Narrowed)")
    print(f"[Check] Hub ISA Hub?               {c_hub.is_subconcept_of(c_hub)} (True: Isa is Reflexive)")
    print(f"[Check] Hub ISA Device?            {c_hub.is_subconcept_of(c_wireless_device)} (True: Role Narrowed)")
    print(f"[Check] Device ISA Sensor?         {c_wireless_device.is_subconcept_of(c_sensor)} (False: Parent is not Child)")
    print(f"[Check] WiredHub ISA Hub?          {c_wired_hub.is_subconcept_of(c_hub)} (False: Hub has no Battery)")
    print(f"[Check] Hub ISA WiredHub?          {c_hub.is_subconcept_of(c_wired_hub)} (True: Hub has More Attributes)")

    # Create Instances (World)
    home_net = PossibleWorld("Home_Network")
    kripke = KripkeStructure()
    kripke.add_world(home_net)
    
    d_sens_ok = {"protocol": "ZigBee", "battery": 95, "role": "Sensor"} # Matches ReliableSensor
    d_sens_low= {"protocol": "ZigBee", "battery": 10, "role": "Sensor"} # Matches Sensor, not Reliable
    d_hub     = {"protocol": "WiFi",   "battery": 100, "role": "Hub"}    # Matches Hub
    
    home_net.add_concept("s1_reliable", d_sens_ok)
    home_net.add_concept("s2_weak", d_sens_low)
    home_net.add_concept("h1_main", d_hub)
    
    print(f"[World] Created objects: s1_reliable, s2_weak, h1_main")
    
    # Check Instances
    print(f"[Instance] Is 's1_reliable' a ReliableSensor? {c_rel_sensor.check(d_sens_ok)}")
    print(f"[Instance] Is 's2_weak' a ReliableSensor?    {c_rel_sensor.check(d_sens_low)}")
    print(f"[Instance] Is 'h1_main' a Hub?               {c_hub.check(d_hub)}")

    print("\n" + "="*50)
    print("TASK 6 & 7: Relations & ISA on Relations")
    print("="*50)
    
    # Base Relation
    rel_connect = LinkFrame("Connection", source_type=c_wireless_device, dest_type=c_wireless_device)
    
    rel_report = LinkFrame("Report", source_type=c_rel_sensor, dest_type=c_hub)
    rel_wired_report = LinkFrame("WiredReport", source_type=c_rel_sensor, dest_type=c_wired_hub)


    print(f"[Defined] {rel_connect.name} ({rel_connect.source_type.name} -> {rel_connect.dest_type.name})")
    print(f"[Defined] {rel_report.name} ({rel_report.source_type.name} -> {rel_report.dest_type.name})")
    
    is_sub = rel_report.is_subframe_of(rel_connect)
    print(f"[Check] Report ISA Connection? {is_sub} (Expected: True)")
    print(f"[Check] WiredReport ISA Connection?    {rel_wired_report.is_subframe_of(rel_connect)} (Expected: False)")

    print("\n" + "="*50)
    print("TASK 8: Relation Instances (Frames)")
    print("="*50)
    
    # Create Valid Frame
    try:
        frame1 = LinkFrameInstance(rel_report, home_net, "s1_reliable", "h1_main")
        print(f"[Frame Created] {frame1}")
    except ValueError as e:
        print(f"[Error] {e}")

    # Check Instance-Of (Transitive)
    check_isa_rel = frame1.is_instance_of(rel_report)
    check_isa_parent = frame1.is_instance_of(rel_connect)
    
    print(f"[Check] Frame ISA Report? {check_isa_rel}")
    print(f"[Check] Frame ISA Connection?     {check_isa_parent} (Inherited)")

    # Invalid Frame (Constraint Violation)
    print("\n[Test] Attempting to link 's2_weak' (Low Battery) as 'Report'...")
    try:
        LinkFrameInstance(rel_report, home_net, "s2_weak", "h1_main")
    except ValueError as e:
        print(f"[Caught Expected Error] {e}")

    print("\n" + "="*50)
    print("Extension Retrieval (Local World)")
    print("="*50)
    
    ext_reliable = home_net.get_extension(c_rel_sensor)
    print(f"[Extension] ReliableSensors in 'Home_Network': {ext_reliable}")

    print("\n" + "="*50)
    print("Reachable Extension (Kripke Worlds)")
    print("="*50)
    
    # Create a reachable world
    world_backup = PossibleWorld("Backup_Network")
    kripke.add_world(world_backup)
    kripke.add_access("Home_Network", "Backup_Network") # Home can access Backup
    
    # Add objects to Backup world
    # s3_backup is a reliable sensor
    d_sens_backup = {"protocol": "ZigBee", "battery": 99, "role": "Sensor"}
    world_backup.add_concept("s3_backup", d_sens_backup)
    
    print("[Setup] Created 'Backup_Network' accessible from 'Home_Network'")
    print("[Setup] Added object 's3_backup' (ReliableSensor) to 'Backup_Network'")
    
    # Query Reachable Extensions from Home_Network
    reachable_ext1 = kripke.get_reachable_extension("Home_Network", c_rel_sensor)
    reachable_ext2 = kripke.get_reachable_extension("Home_Network", c_hub)
    
    print(f"\n[Query] Get reachable ReliableSensors starting from 'Home_Network'...")
    print(f"[Result] {reachable_ext1}")

    print(f"\n[Query] Get reachable Hub starting from 'Home_Network'...")
    print(f"[Result] {reachable_ext2}")

if __name__ == "__main__":
    run_scenario()