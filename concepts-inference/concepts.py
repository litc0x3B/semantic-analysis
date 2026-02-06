from typing import Any, Dict, Set, List, Optional, NamedTuple, Tuple
from enum import Enum
import operator


class Role(Enum):
    INITIATOR = "Initiator"
    RECEIVER = "Receiver"
    CONTROLLER = "Controller"
    MANAGED = "Managed"
    GATEWAY = "Gateway"
    TIMESTAMP = "Timestamp"
    NODE = "Node"


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

        if self.min_val > self.max_val:
            raise ValueError("Minimum value cannot be greater than maximum value")


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

        if not self.allowed:
            raise ValueError("Set of allowed values cannot be empty")


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

    def __and__(self, other: 'BaseConcept'):
        return self.intersect(other, f"({self.name}^{other.name})" if self.name != other.name else self.name)
    
    def intersect(self, other: 'BaseConcept', name: str) -> 'BaseConcept':
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
            if other.name not in attrs:
                attrs[other.name] = other
            else:
                attrs[other.name] = AtomicConcept(other.name, other.constraint.intersect(attrs[other.name].constraint))
            
        return CompositeConcept(name, attrs)

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
        attrs_str = ", ".join([str(atom) for atom in self.attributes.values()])
        return f"Concept[{self.name}]({attrs_str})"

class FrameArgInfo(NamedTuple):
    name: str
    role: Role
    type: BaseConcept
    

class Frame:
    def __init__(self, name: str, argsInfo: List[FrameArgInfo]):
        self.name = name
        self.argsInfo = dict([(x.name, x) for x in argsInfo])
        self._intersection = set([self])

    def __and__(self, other: 'Frame'):
        return self.intersect(other, f"({self.name}^{other.name})")
        
    
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
        args_str = ", ".join([f"{v.role.value}->{v.name}:{v.type.name}" for v in self.argsInfo.values()])
        return f"Frame[{self.name}]({args_str})"


class ConceptInstance:
    def __init__(self, uid: str, data: Dict[str, Any]):
        self.uid = uid
        self.data = data
    
    def __repr__(self):
        return f"Inst(name: {self.uid}, data:{self.data})"


class PossibleWorld:
    def __init__(self, name):
        self.name = name
        self.concepts: Dict[str, ConceptInstance] = {} 
        self.frames: List['FrameInstance'] = []

    def add_concept(self, uid: str, data: Dict[str, Any]) -> 'PossibleWorld':
        self.concepts[uid] = ConceptInstance(uid, data)
        return self
    
    def add_frame(self, frame_inst: 'FrameInstance') -> 'PossibleWorld':
        self.frames.append(frame_inst)
        return self
    
    def get_concept(self, uid: str) -> Optional[ConceptInstance]:
        return self.concepts.get(uid)

    def get_extension(self, concept: BaseConcept) -> List[ConceptInstance]:
        return [inst for inst in self.concepts.values() if concept.check(inst.data)]

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

    def get_reachable_extension(self, start_world_name: str, concept: BaseConcept) -> Dict[str, List[ConceptInstance]]:
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


class FrameInstance:
    def __init__(self, frame: Frame, args: Dict[str, ConceptInstance]):
        self.frame = frame
        self.args = args
        self._validate()

    def _validate(self):
        # 1. Validate argument presence
        required_args = set(self.frame.argsInfo.keys())
        provided_args = set(self.args.keys())
        
        if required_args != provided_args:
             raise ValueError(f"Frame arguments mismatch. Required: {required_args}, Provided: {provided_args}")

        # 2. Validate types
        for var_name, concept_inst in self.args.items():
            arg_info = self.frame.argsInfo[var_name]
            if not arg_info.type.check(concept_inst.data):
                raise ValueError(
                    f"Argument '{var_name}' (uid='{concept_inst.uid}') violates type '{arg_info.type.name}'"
                )

    def __repr__(self):
        parts = []
        for var_name, inst in self.args.items():
            arg_info = self.frame.argsInfo[var_name]
            parts.append(f"{arg_info.role.value}->{inst.uid}:{arg_info.type.name}")
        return f"FrameInstance[{self.frame.name}]({', '.join(parts)})"
    
    def is_instance_of(self, target_frame: Frame) -> bool:
        return self.frame.is_subframe_of(target_frame)


def run_scenario():
    print("\n" + "="*50)
    print("Define Concepts")
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
    с_device = atom_proto_any & atom_bat_any & atom_role_dev
    с_device.name = "Device"
    
    c_sensor = atom_proto_zig & atom_bat_any & atom_role_sen
    c_sensor.name = "Sensor"

    c_rel_sensor = c_sensor & atom_bat_full
    c_rel_sensor.name = "ReliableSensor"
    
    c_hub = с_device & atom_role_hub
    c_hub.name = "Hub"
    

    print(f"[Defined] {с_device.name}")
    print(f"[Defined] {c_sensor.name}")
    print(f"[Defined] {c_rel_sensor.name}")
    print(f"[Defined] {c_hub.name}")

    print("\n" + "="*50)
    print("Concept ISA & Instances Checks")
    print("="*50)

    # Check ISA
    print(f"[Check] ReliableSensor ISA Sensor? {c_rel_sensor.is_subconcept_of(c_sensor)} (True: Constraints Narrowed)")
    print(f"[Check] Hub ISA Device?    {c_hub.is_subconcept_of(с_device)} (True: Role Narrowed)")
    print(f"[Check] Device ISA Sensor? {с_device.is_subconcept_of(c_sensor)} (False: Parent is not Child)")

    # Create World
    world = PossibleWorld("Home")
    
    # Concept Instances
    world.add_concept("hub_main", {"protocol": "WiFi",   "battery": 100, "role": "Hub"})
    world.add_concept("hub_bridge", {"protocol": "WiFi", "battery": 100, "role": "Hub"})
    world.add_concept("sensor_1", {"protocol": "ZigBee", "battery": 90,  "role": "Sensor"})
    world.add_concept("sensor_weak", {"protocol": "ZigBee", "battery": 10, "role": "Sensor"})

    print(f"[World] Created Concept Instances: hub_main, hub_bridge, sensor_1, sensor_weak")

    # Check Instances
    h_main_data = world.get_concept("hub_main").data
    s1_data = world.get_concept("sensor_1").data
    sw_data = world.get_concept("sensor_weak").data

    print(f"[Instance] Is 'hub_main' a Hub?               {c_hub.check(h_main_data)}")
    print(f"[Instance] Is 'sensor_1' a ReliableSensor?    {c_rel_sensor.check(s1_data)}")
    print(f"[Instance] Is 'sensor_weak' a ReliableSensor? {c_rel_sensor.check(sw_data)} (False: Low Battery)")

    print("\n" + "="*50)
    print("Extensions (Local World)")
    print("="*50)
    
    ext_hubs = world.get_extension(c_hub)
    ext_rel_sensors = world.get_extension(c_rel_sensor)
    
    print(f"[Extension] Hubs: {ext_hubs}")
    print(f"[Extension] Reliable Sensors: {ext_rel_sensors}")


    print("\n" + "="*50)
    print("Frame Definitions & Partial Overlap Intersection")
    print("="*50)

    # Фрейм управления: Кто-то управляет чем-то
    f_control = Frame("Control", [
        FrameArgInfo(name="actor",  role=Role.CONTROLLER, type=c_hub),
        FrameArgInfo(name="target", role=Role.MANAGED,    type=с_device)
    ])

    # Фрейм сетевой привязки: Устройство подключено к шлюзу
    f_topology = Frame("Topology", [
        FrameArgInfo(name="target",  role=Role.MANAGED, type=с_device),
        FrameArgInfo(name="gateway", role=Role.GATEWAY, type=c_hub)
    ])

    # Фрейм-ограничитель: Цель должна быть сенсором
    f_sensor_target = Frame("SensorTarget", [
        FrameArgInfo(name="target", role=Role.MANAGED, type=c_sensor)
    ])

    print(f"[Defined] {f_control}")
    print(f"[Defined] {f_topology}")
    print(f"[Defined] {f_sensor_target}")
    
    print("\n--- Intersection Scenarios ---")
    
    # Case A: Partial Overlap (actor, target) & (target, gateway)
    # Result should have variables: actor, target, gateway
    f_routed_control = f_control & f_topology
    f_routed_control.name = "RoutedControl"
    print(f"\n[Intersect Partial Overlap] {f_control.name} & {f_topology.name}")
    print(f"Result: {f_routed_control}")
    
    # Case B: Type Narrowing on a 3-argument frame
    # RoutedControl & SensorTarget -> target type narrows to Sensor
    f_secure_routed = f_routed_control & f_sensor_target
    f_secure_routed.name = "SecureRoutedControl"
    print(f"\n[Intersect Type Narrowing] {f_routed_control.name} & {f_sensor_target.name}")
    print(f"Result: {f_secure_routed}")

    print("\n" + "="*50)
    print("Frame Instances & Validation")
    print("="*50)
    
    # Reuse World 'Home' created earlier
    
    print("[World] Using existing concept instances: hub_main, hub_bridge, sensor_1")

    # Retrieve instances
    h_main = world.get_concept("hub_main")
    h_bridge = world.get_concept("hub_bridge")
    s1 = world.get_concept("sensor_1")

    # 1. Valid Instance of RoutedControl (3 args)
    print("\n[Test] Creating valid 'RoutedControl' instance (hub_main -> sensor_1 via hub_bridge)...")
    try:
        inst1 = FrameInstance(f_routed_control, {
            "actor": h_main,
            "target": s1,
            "gateway": h_bridge
        })
        world.add_frame(inst1)
        print(f"[Success] {inst1}")
    except ValueError as e:
        print(f"[Failed] {e}")

    # 2. Valid Instance of SecureRoutedControl
    print("\n[Test] Creating valid 'SecureRoutedControl' instance...")
    try:
        inst2 = FrameInstance(f_secure_routed, {
            "actor": h_main,
            "target": s1,
            "gateway": h_bridge
        })
        world.add_frame(inst2)
        print(f"[Success] {inst2}")
    except ValueError as e:
        print(f"[Failed] {e}")

    # 3. Invalid Instance (Target is Hub, but SecureRoutedControl requires Sensor)
    print("\n[Test] Creating invalid 'SecureRoutedControl' (Target is Hub)...")
    try:
        FrameInstance(f_secure_routed, {
            "actor": h_main,
            "target": h_bridge, # hub_bridge is Hub, not Sensor
            "gateway": h_main
        })
    except ValueError as e:
        print(f"[Caught Expected Error] {e}")

    print("\n" + "="*50)
    print("Kripke & Extensions Check")
    print("="*50)
    
    print(f"[World] Frames in 'Home' world: {world.frames}")
    
    # Create Kripke Structure
    kripke = KripkeStructure()
    kripke.add_world(world)
    
    # Create another world 'Garage'
    world_garage = PossibleWorld("Garage")
    world_garage.add_concept("sensor_garage", {"protocol": "ZigBee", "battery": 85, "role": "Sensor"})
    kripke.add_world(world_garage)
    
    # Link Home -> Garage
    kripke.add_access("Home", "Garage")
    
    print("[Kripke] Added world 'Garage' accessible from 'Home'")
    print("[Kripke] Added concept instance 'sensor_garage' to 'Garage'")
    
    # Check reachable extension
    reachable = kripke.get_reachable_extension("Home", c_rel_sensor)
    print(f"[Query] Reachable ReliableSensors starting from 'Home': {reachable}")

    print("\n" + "="*50)
    print("ISA on Frames (Subframe Relationships)")
    print("="*50)
    
    # A frame created by intersection is a subframe of its components
    print(f"[Check] RoutedControl ISA Control?  {f_routed_control.is_subframe_of(f_control)} (True)")
    print(f"[Check] RoutedControl ISA Topology? {f_routed_control.is_subframe_of(f_topology)} (True)")
    print(f"[Check] Control ISA RoutedControl?  {f_control.is_subframe_of(f_routed_control)} (False)")
    
    # Check instance membership
    inst_routed = FrameInstance(f_routed_control, {"actor": h_main, "target": s1, "gateway": h_bridge})
    print(f"\n[Instance] Created {inst_routed}")
    print(f"[Check] Is instance of RoutedControl? {inst_routed.is_instance_of(f_routed_control)} (True)")
    print(f"[Check] Is instance of Control?       {inst_routed.is_instance_of(f_control)} (true)")
    print(f"[Check] Is instance of Topology?      {inst_routed.is_instance_of(f_topology)} (true)")

    inst_control = FrameInstance(f_control, {"actor": h_main, "target": s1})
    print(f"\n[Instance] Created {inst_control}")
    print(f"[Check] Is instance of RoutedControl? {inst_control.is_instance_of(f_routed_control)} (True)")
    print(f"[Check] Is instance of Control?       {inst_control.is_instance_of(f_control)} (true)")
    print(f"[Check] Is instance of Topology?      {inst_control.is_instance_of(f_topology)} (true)")
    


if __name__ == "__main__":
    run_scenario()