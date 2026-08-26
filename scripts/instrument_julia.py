from __future__ import annotations

from pathlib import Path


path = Path("sourceforge/csvplan.jl")
text = path.read_text(encoding="utf-8")

needle = "    computeHarmonies(baseScenario)\n    iter = 1\n"
replacement = (
    "    computeHarmonies(baseScenario)\n"
    "    println(\"TRACE_INITIAL,\",baseScenario.meanh,\",\",baseScenario.stdh,\",\",join(baseScenario.h,\";\"))\n"
    "    iter = 1\n"
)
if needle not in text:
    raise SystemExit("initial instrumentation anchor not found")
text = text.replace(needle, replacement, 1)

needle = "    return bestscenario\nend\nfunction Estimate_how_much__production_to_be_scaled_up"
replacement = (
    "    println(\"TRACE_CHOICE,\",destyear,\",\",bestyear,\",\",bestgain,\",\",bestscenario.meanh,\",\",join(bestscenario.h,\";\"))\n"
    "    return bestscenario\n"
    "end\n"
    "function Estimate_how_much__production_to_be_scaled_up"
)
if needle not in text:
    raise SystemExit("choice instrumentation anchor not found")
text = text.replace(needle, replacement, 1)

needle = "        if !doagain\n            for yr = 1:problem.TheLastYear-depreciationhorizon\n"
replacement = (
    "        if !doagain\n"
    "            println(\"TRACE_FINAL,\",iter,\",\",baseScenario.meanh,\",\",baseScenario.stdh,\",\",baseScenario.stdh/abs(baseScenario.meanh),\",\",join(baseScenario.h,\";\"))\n"
    "            println(\"TRACE_FINAL_INVESTMENTS,\",join(vec(sum(baseScenario.investments,dims=(2,3))),\";\"))\n"
    "            println(\"TRACE_FINAL_GOALRATIOS,\",join(baseScenario.goal_fullfilment_ratio_vector,\";\"))\n"
    "            for yr = 1:problem.TheLastYear-depreciationhorizon\n"
)
if needle not in text:
    raise SystemExit("final instrumentation anchor not found")
text = text.replace(needle, replacement, 1)

path.write_text(text, encoding="utf-8")
print("instrumented", path)
