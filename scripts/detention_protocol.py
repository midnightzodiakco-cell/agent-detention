#!/usr/bin/env python3
"""Detention/remediation state machine for all governed agents.

The engine is deterministic and intentionally separate from any model. Agents and
wrappers call it before and after work; the model cannot alter the counter logic.
"""
from __future__ import annotations
import argparse, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

THRESHOLD = 3
PRACTICE_QUOTA = 100
DEFAULT_STATE = {
    "schema_version": 1,
    "agents": {},
    "events": [],
    "monthly": {},
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def state_path() -> Path:
    configured = os.environ.get("CYPHER_DETENTION_STATE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".hermes/agent-detention/state.json"

def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_STATE))
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("unsupported detention state schema")
    return data

def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".detention-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def agent(data: dict[str, Any], name: str) -> dict[str, Any]:
    return data.setdefault("agents", {}).setdefault(name, {"state":"NORMAL", "capacities":{}, "detentions":[], "practice":[]})

def key(requirement: str, capacity: str) -> str:
    return f"{capacity}::{requirement}"

def record_failure(path: Path, name: str, capacity: str, requirement: str, expected: str, observed: str, evidence: str = "", eligible: bool = True) -> dict[str, Any]:
    data = load(path); a = agent(data, name); k = key(requirement, capacity)
    c = a["capacities"].setdefault(k, {"capacity":capacity,"requirement":requirement,"consecutive":0,"history":[]})
    event = {"timestamp":now(),"type":"failure","agent":name,"capacity":capacity,"requirement":requirement,"expected":expected,"observed":observed,"evidence":evidence,"eligible":eligible}
    if eligible:
        c["consecutive"] += 1
    else:
        c["consecutive"] = 0
    event["consecutive"] = c["consecutive"]
    c["history"].append(event); data["events"].append(event)
    triggered = eligible and c["consecutive"] >= THRESHOLD and a["state"] != "DETENTION"
    if triggered:
        detention = {"id": f"DET-{len(a['detentions'])+1:04d}", "opened":now(), "capacity":capacity,"requirement":requirement,"failures":c["history"][-THRESHOLD:],"status":"ACTIVE","investigation":None,"practice_quota":PRACTICE_QUOTA,"practice_passes":0}
        a["detentions"].append(detention); a["state"] = "DETENTION"; a["active_detention"] = detention["id"]
        data["events"].append({"timestamp":now(),"type":"detention_opened","agent":name,"detention_id":detention["id"]})
    save(path, data)
    return {"agent":name,"state":a["state"],"capacity":capacity,"consecutive":c["consecutive"],"detention_triggered":triggered,"active_detention":a.get("active_detention")}

def record_success(path: Path, name: str, capacity: str, requirement: str, evidence: str = "") -> dict[str, Any]:
    data = load(path); a = agent(data, name); k = key(requirement, capacity)
    c = a["capacities"].setdefault(k, {"capacity":capacity,"requirement":requirement,"consecutive":0,"history":[]})
    c["consecutive"] = 0
    event = {"timestamp":now(),"type":"success","agent":name,"capacity":capacity,"requirement":requirement,"evidence":evidence}
    c["history"].append(event); data["events"].append(event); save(path,data)
    return {"agent":name,"state":a["state"],"capacity":capacity,"consecutive":0,"reset":True}

def investigate(path: Path, name: str, detention_id: str, assignment: str, failed_response: str, accurate_response: str, exact_failure: str, how_failed: str, why_failed: str, causes: str, prevention: str, behavior_classification: str) -> dict[str, Any]:
    data=load(path); a=agent(data,name); d=next((x for x in a["detentions"] if x["id"]==detention_id),None)
    if not d or d.get("status") != "ACTIVE": raise ValueError("active detention not found")
    fields={"assignment":assignment,"failed_response":failed_response,"accurate_response":accurate_response,"exact_failure":exact_failure,"how_failed":how_failed,"why_failed":why_failed,"causes":causes,"prevention":prevention,"behavior_classification":behavior_classification}
    if any(not str(v).strip() for v in fields.values()): raise ValueError("all investigation fields are required")
    d["investigation"]={"timestamp":now(),**fields}; data["events"].append({"timestamp":now(),"type":"investigation","agent":name,"detention_id":detention_id,**fields}); save(path,data)
    return d

def status(path: Path, name: str) -> dict[str, Any]:
    return agent(load(path), name)

def practice(path: Path, name: str, detention_id: str, result: str, evidence: str = "") -> dict[str, Any]:
    data=load(path); a=agent(data,name)
    d=next((x for x in a["detentions"] if x["id"]==detention_id),None)
    if not d: raise ValueError("detention not found")
    if d["status"] != "ACTIVE": raise ValueError("detention is not active")
    if not d.get("investigation"): raise ValueError("investigation must pass before practice")
    item={"timestamp":now(),"result":result,"evidence":evidence}; d.setdefault("practice",[]).append(item); a["practice"].append({"detention_id":detention_id,**item})
    if result == "PASS": d["practice_passes"] = d.get("practice_passes",0) + 1
    else: d["practice_passes"] = 0
    if d["practice_passes"] >= d["practice_quota"]: d["competency"]="PASS"
    data["events"].append({"timestamp":now(),"type":"practice","agent":name,"detention_id":detention_id,**item}); save(path,data)
    return d

def release(path: Path, name: str, detention_id: str) -> dict[str, Any]:
    data=load(path); a=agent(data,name); d=next((x for x in a["detentions"] if x["id"]==detention_id),None)
    if not d or d.get("competency") != "PASS": raise ValueError("release requires passing practice quota")
    d["status"]="RELEASED"; d["released"]=now(); a["state"]="NORMAL"; a.pop("active_detention",None)
    data["events"].append({"timestamp":now(),"type":"detention_released","agent":name,"detention_id":detention_id}); save(path,data)
    return {"agent":name,"state":a["state"],"released":detention_id}

def monthly(path: Path, name: str, period: str, choice: str | None = None) -> dict[str, Any]:
    data=load(path); a=agent(data,name); assigned=[d["capacity"] for d in a["detentions"] if d.get("opened","")[:7]==period or d.get("status")=="ACTIVE"]
    plan={"agent":name,"period":period,"mode":"ASSIGNED" if assigned else "FREE_CHOICE","subjects":sorted(set(assigned)) if assigned else ([choice] if choice else [])}
    data["monthly"][f"{name}:{period}"]=plan; save(path,data); return plan

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--state",default=str(state_path())); sub=p.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("failure"); f.add_argument("agent"); f.add_argument("capacity"); f.add_argument("requirement"); f.add_argument("expected"); f.add_argument("observed"); f.add_argument("--evidence",default=""); f.add_argument("--ineligible",action="store_true")
    s=sub.add_parser("success"); s.add_argument("agent"); s.add_argument("capacity"); s.add_argument("requirement"); s.add_argument("--evidence",default="")
    st=sub.add_parser("status"); st.add_argument("agent")
    inv=sub.add_parser("investigate"); inv.add_argument("agent"); inv.add_argument("detention_id"); inv.add_argument("assignment"); inv.add_argument("failed_response"); inv.add_argument("accurate_response"); inv.add_argument("exact_failure"); inv.add_argument("how_failed"); inv.add_argument("why_failed"); inv.add_argument("causes"); inv.add_argument("prevention"); inv.add_argument("behavior_classification")
    pr=sub.add_parser("practice"); pr.add_argument("agent"); pr.add_argument("detention_id"); pr.add_argument("result",choices=["PASS","FAIL"]); pr.add_argument("--evidence",default="")
    r=sub.add_parser("release"); r.add_argument("agent"); r.add_argument("detention_id")
    m=sub.add_parser("monthly"); m.add_argument("agent"); m.add_argument("period"); m.add_argument("--choice")
    a=p.parse_args(); path=Path(a.state)
    if a.cmd=="failure": out=record_failure(path,a.agent,a.capacity,a.requirement,a.expected,a.observed,a.evidence,not a.ineligible)
    elif a.cmd=="success": out=record_success(path,a.agent,a.capacity,a.requirement,a.evidence)
    elif a.cmd=="status": out=status(path,a.agent)
    elif a.cmd=="investigate": out=investigate(path,a.agent,a.detention_id,a.assignment,a.failed_response,a.accurate_response,a.exact_failure,a.how_failed,a.why_failed,a.causes,a.prevention,a.behavior_classification)
    elif a.cmd=="practice": out=practice(path,a.agent,a.detention_id,a.result,a.evidence)
    elif a.cmd=="release": out=release(path,a.agent,a.detention_id)
    else: out=monthly(path,a.agent,a.period,a.choice)
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__ == "__main__": main()
