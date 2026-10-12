// Lists callers of FF8's icon.sp1 draw functions and, per caller, the icon-id immediates nearby.
// Args: function entry addresses (hex). Also resolves "call@<addr>" to the call target first.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.scalar.Scalar;
import java.util.*;

public class IconCallers extends GhidraScript {
    @Override public void run() throws Exception {
        Listing L = currentProgram.getListing();
        List<Address> targets = new ArrayList<>();
        for (String s : getScriptArgs()) {
            if (s.startsWith("call@")) {
                Address a = toAddr(s.substring(5));
                Instruction ins = L.getInstructionAt(a);
                Address t = ins.getFlows().length > 0 ? ins.getFlows()[0] : null;
                println("call at " + a + " -> " + t);
                if (t != null) targets.add(t);
            } else targets.add(toAddr(s));
        }
        for (Address t : targets) {
            Function tf = getFunctionAt(t);
            println("=== callers of " + t + " " + (tf != null ? tf.getName() : ""));
            Map<Function, List<Address>> by = new TreeMap<>(Comparator.comparing(Function::getEntryPoint));
            for (Reference r : getReferencesTo(t)) {
                if (!r.getReferenceType().isCall()) continue;
                Function f = getFunctionContaining(r.getFromAddress());
                if (f == null) continue;
                by.computeIfAbsent(f, k -> new ArrayList<>()).add(r.getFromAddress());
            }
            for (Map.Entry<Function, List<Address>> e : by.entrySet()) {
                Function f = e.getKey();
                // immediates 0x80..0x8B anywhere in the caller (button icon ids)
                TreeSet<Long> imms = new TreeSet<>();
                for (Instruction ins : L.getInstructions(f.getBody(), true))
                    for (int op = 0; op < ins.getNumOperands(); op++)
                        for (Object o : ins.getOpObjects(op))
                            if (o instanceof Scalar) {
                                long v = ((Scalar) o).getUnsignedValue();
                                if (v >= 0x80 && v <= 0x8B) imms.add(v);
                            }
                println(String.format("  %s %s size=%d calls=%d btnImm=%s", f.getEntryPoint(), f.getName(),
                        f.getBody().getNumAddresses(), e.getValue().size(), imms));
            }
        }
    }
}
