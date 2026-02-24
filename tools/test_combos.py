#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


COMBOS = [
    {
        "id": "A",
        "name": "Build Underground + Stable Life Support",
        "items": [1, 4, 8, 9],
        "habitation": "subsurface",
    },
    {
        "id": "B",
        "name": "Print Shielding + Stable Life Support",
        "items": [1, 7, 8, 9],
        "habitation": "partial",
    },
    {
        "id": "C",
        "name": "Reliability-First Survival",
        "items": [1, 8, 9, 13],
        "habitation": "partial",
    },
    {
        "id": "D",
        "name": "Thermal + Life Support",
        "items": [1, 11, 8, 9],
        "habitation": "partial",
    },
    {
        "id": "E",
        "name": "Solar Path Probe",
        "items": [2, 3, 8, 7],
        "habitation": "partial",
    },
]

BUDGETS = [12, 13, 14, 16]


def _build_jxa_source() -> str:
    return r"""ObjC.import('Foundation');

function readText(path){
  const p = $(String(path)).stringByStandardizingPath;
  const data = $.NSData.dataWithContentsOfFile(p);
  if(!data) throw new Error('Unable to read: ' + path);
  return ObjC.unwrap($.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding));
}

function makeEl(){
  const noop=function(){};
  return {
    style:{},
    classList:{add:noop,remove:noop,toggle:noop,contains:function(){return false;}},
    addEventListener:noop,
    removeEventListener:noop,
    appendChild:noop,
    remove:noop,
    querySelectorAll:function(){return [];},
    querySelector:function(){return null;},
    innerHTML:'',
    textContent:'',
    value:'',
    readOnly:false
  };
}

function installStubs(){
  const noop=function(){};
  const els={};
  this.document={
    getElementById:function(id){
      if(!els[id]) els[id]=makeEl();
      return els[id];
    },
    querySelectorAll:function(){return [];},
    querySelector:function(){return null;},
    createElement:function(){return makeEl();},
    body:makeEl()
  };
  this.window={location:{search:''},addEventListener:noop,scrollTo:noop};
  this.confirm=function(){return true;};
  this.alert=noop;
  this.setTimeout=function(){return 0;};
  this.clearTimeout=noop;
  this.setInterval=function(){return 0;};
  this.clearInterval=noop;
  this.Chart=function(){return {destroy:noop};};
  this.firebase={
    apps:[],
    initializeApp:noop,
    database:function(){
      return {
        ref:function(){
          const ref={
            once:function(){return Promise.resolve({val:function(){return null;}});},
            on:noop,
            off:noop,
            set:noop,
            update:noop,
            remove:noop,
            child:function(){return ref;}
          };
          return ref;
        }
      };
    }
  };
}

function extractScript(html){
  const m = html.match(/<script>([\s\S]*?)<\/script>\s*<\/body>/);
  if(!m) throw new Error('Inline app script not found in index.html');
  return m[1];
}

function selectHabitation(tc){
  const requested=(tc.habitation||'surface').toLowerCase();
  return {hab:requested, notes:[]};
}

function getAtOrBefore(arr, sol, key){
  if(!Array.isArray(arr)||arr.length===0) return null;
  const sorted=arr.slice().sort(function(a,b){return Number(a.sol)-Number(b.sol);});
  for(let i=0;i<sorted.length;i++){
    if(Number(sorted[i].sol)===Number(sol)) return sorted[i][key];
  }
  let prior=null;
  for(let i=0;i<sorted.length;i++){
    if(Number(sorted[i].sol)<=Number(sol)) prior=sorted[i];
  }
  return prior ? prior[key] : sorted[0][key];
}

function weakestFromFinal(finalIdx){
  const pairs=Object.keys(finalIdx).map(function(k){return {k:k,v:Number(finalIdx[k]||0)};});
  pairs.sort(function(a,b){return a.v-b.v;});
  return pairs.slice(0,2).map(function(x){return x.k;});
}

function buildHints(entry){
  const hints=[];
  const reason=String(entry.failReason||'');
  if(reason.indexOf('Transport')!==-1) hints.push('Increase MU budget or reduce MU total.');
  if(Number(entry.finalIndices.PS)<55) hints.push('Power deficit: reduce draws or increase generation.');
  if(Number(entry.finalIndices.RS)<55 || reason.toLowerCase().indexOf('radiation')!==-1) hints.push('Improve shielding or move underground earlier.');
  if(Number(entry.finalIndices.LS)<55) hints.push('Water/O2 instability: check item_08/item_09 and late penalties.');
  if(Number(entry.finalIndices.ER)<40) hints.push('High breakdown risk: repair toolkit or reduce dust exposure.');
  return hints;
}

function runReport(payload){
  const budgets=payload.budgets||[];
  const combos=payload.combos||[];
  const out=[];
  budgets.forEach(function(budget){
    combos.forEach(function(tc){
      const pick=selectHabitation(tc);
      const result=simulate(tc.items, pick.hab, budget);
      const power=(result.powerTimeline||[]).map(function(p){
        return {
          sol:Number(p.sol),
          genKW:Number(p.genKW||0),
          drawKW:Number(p.drawKW||0),
          netKW:Number(p.netKW||0)
        };
      });
      const rad=(result.radiationTimeline||[]).map(function(r){
        return {
          sol:Number(r.sol),
          cumDose:Number(r.cumDose||0),
          RS:Number(r.RS||0)
        };
      });
      const finalIndices={
        RS:Number(getAtOrBefore(result.radiationTimeline,180,'RS')||0),
        PS:Number(getAtOrBefore(result.powerTimeline,180,'PS')||0),
        LS:Number(getAtOrBefore(result.lsTimeline,180,'LS')||0),
        ER:Number(getAtOrBefore(result.erTimeline,180,'ER')||0),
        CS:Number(getAtOrBefore(result.csTimeline,180,'CS')||0),
      };
      const itemMu=getSelectedMu(tc.items);
      const entry={
        comboId:tc.id,
        comboName:tc.name,
        items:tc.items.slice(),
        habitationRequested:tc.habitation,
        habitationUsed:result.habitationUsed||result.habitation||pick.hab,
        notes:pick.notes.slice(),
        muBudget:Number(budget),
        muTotal:Number(itemMu),
        transportStatus:result.transportStatus||'OK',
        status:result.status||result.resultLabel||'NON-VIABLE',
        viabilityScore:Number(result.viability100||0),
        failIdx:result.failIdx||null,
        failDay:result.failDay===null?null:Number(result.failDay),
        failReason:result.failReason||null,
        weakestIndices:weakestFromFinal(finalIndices),
        finalIndices:finalIndices,
        powerTimeline:power,
        radiationTimeline:rad,
        rawResult:result
      };
      if(result.invalid && result.invalidReason){
        if(/partial subsurface|fully subsurface/i.test(result.invalidReason)){
          entry.notes.push('gating issue: requested habitation does not meet enabler requirements');
        }
        entry.notes.push('invalid: ' + result.invalidReason);
      }
      entry.hints=buildHints(entry);
      out.push(entry);
    });
  });

  const passRateByBudget={};
  budgets.forEach(function(b){
    const rows=out.filter(function(x){return Number(x.muBudget)===Number(b);});
    passRateByBudget[String(b)]={viable:0,marginal:0,nonViable:0};
    rows.forEach(function(r){
      if(r.status==='VIABLE') passRateByBudget[String(b)].viable+=1;
      else if(r.status==='MARGINAL') passRateByBudget[String(b)].marginal+=1;
      else passRateByBudget[String(b)].nonViable+=1;
    });
  });

  return {
    generatedAt:(new Date()).toISOString(),
    budgets:budgets,
    combos:combos.map(function(c){return {id:c.id,name:c.name,items:c.items,habitation:c.habitation};}),
    results:out,
    passRateByBudget:passRateByBudget
  };
}

function run(args){
  const indexPath=args[0];
  const payload=JSON.parse(args[1]);
  installStubs();
  const html=readText(indexPath);
  let appScript=extractScript(html);
  appScript=appScript.replace(/\ninit\(\);\s*$/,'\n');
  const loader = new Function(
    appScript + '\nreturn {simulate:(typeof simulate!==\"undefined\"?simulate:null),getSelectedMu:(typeof getSelectedMu!==\"undefined\"?getSelectedMu:null)};'
  );
  const exported = loader();
  if(!exported || typeof exported.simulate!=='function'){
    throw new Error('simulate() not found after loading app script');
  }
  this.simulate = exported.simulate;
  this.getSelectedMu = exported.getSelectedMu;
  const report=runReport(payload);
  return JSON.stringify(report);
}
"""


def _run_report(index_path: Path, combos: list[dict], budgets: list[int]) -> dict:
    payload = {"combos": combos, "budgets": budgets}
    jxa_source = _build_jxa_source()
    with tempfile.NamedTemporaryFile("w", suffix=".jxa", delete=False) as tmp:
        tmp.write(jxa_source)
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", str(tmp_path), str(index_path), json.dumps(payload)],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "osascript failed with "
            f"code={proc.returncode}\nstdout:\n{(proc.stdout or '').strip()}\nstderr:\n{(proc.stderr or '').strip()}"
        )
    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError(f"No output from osascript. stderr={proc.stderr.strip()}")
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Could not parse JSON from osascript output:\n{raw}\n{proc.stderr}")
    return json.loads(raw[start : end + 1])


def _fmt_short(text: str | None, width: int) -> str:
    s = (text or "-").replace("\n", " ").strip()
    return (s[: width - 1] + "…") if len(s) > width else s


def _print_console_report(report: dict) -> None:
    by_budget: dict[int, list[dict]] = {}
    for row in report["results"]:
        by_budget.setdefault(int(row["muBudget"]), []).append(row)

    for budget in report["budgets"]:
        rows = by_budget.get(int(budget), [])
        print(f"\n=== MU BUDGET {budget} ===")
        print(
            f"{'COMBO':<8} {'MU':<7} {'TRANSPORT':<10} {'STATUS':<11} {'SCORE':<6} {'FAIL':<7} {'IDX':<5} {'REASON'}"
        )
        for r in rows:
            fail = "-" if r["failDay"] is None else f"D{r['failDay']}"
            mu_pair = f"{r['muTotal']}/{r['muBudget']}"
            print(
                f"{r['comboId']:<8} {mu_pair:<7} {r['transportStatus']:<10} "
                f"{r['status']:<11} {r['viabilityScore']:<6} {fail:<7} {_fmt_short(r['failIdx'], 5):<5} {_fmt_short(r['failReason'], 64)}"
            )
            idx = r["finalIndices"]
            weakest = ",".join(r["weakestIndices"])
            print(
                f"  idx180 RS:{idx['RS']:.1f} PS:{idx['PS']:.1f} LS:{idx['LS']:.1f} ER:{idx['ER']:.1f} CS:{idx['CS']:.1f} | weakest: {weakest}"
            )
            pwr = " | ".join(
                f"{p['sol']}: {p['genKW']:.1f}/{p['drawKW']:.1f}/{p['netKW']:.1f}" for p in r["powerTimeline"]
            )
            rad = " | ".join(f"{x['sol']}: dose {x['cumDose']:.1f}" for x in r["radiationTimeline"])
            print(f"  power(sol gen/draw/net): {pwr}")
            print(f"  radiation(cumulative): {rad}")
            if r["notes"]:
                print(f"  notes: {'; '.join(r['notes'])}")
            if r["hints"]:
                print(f"  hints: {'; '.join(r['hints'])}")

    print("\n=== PASS RATE SUMMARY ===")
    for budget in report["budgets"]:
        s = report["passRateByBudget"][str(budget)]
        print(
            f"MU {budget}: VIABLE={s['viable']}  MARGINAL={s['marginal']}  NON-VIABLE={s['nonViable']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run combo test harness using the live simulator from index.html.")
    parser.add_argument("--index", default="index.html", help="Path to HTML app file (default: index.html)")
    parser.add_argument("--out-dir", default="reports", help="Directory for JSON report artifacts")
    parser.add_argument("--smoke", action="store_true", help="Run only 1 combo and 1 budget (for CI/smoke tests)")
    parser.add_argument("--json-only", action="store_true", help="Skip console tables; only emit artifact path")
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    if not index_path.exists():
        raise FileNotFoundError(f"Missing index file: {index_path}")

    combos = COMBOS[:1] if args.smoke else COMBOS
    budgets = [12] if args.smoke else BUDGETS
    report = _run_report(index_path, combos, budgets)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"combo_test_report_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not args.json_only:
        _print_console_report(report)
    print(f"\nREPORT_FILE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
