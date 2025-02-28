# Bifrost_BSL
Experimental Bifrost Scripting Language

## What this is not
- not an evaluation engine. You still need Bifrost
- a polished product. This is a rough proof of concept that grew into the monstrosity it is because I did not anticipate certain changes and challenges. This version was never intended to see the light of day but here we are... Look at the code at your own risk. It's neither clean, nor commented, nor well formatted
- not higher or lower level than Bifrost
- not a language like VEX that compiles with the graph

## What this is
- a transpiler that uses vnn to create an equivalent Bifrost graph. JSON and XML are planned, but not yet supported
- strongly typed, tightly scoped, and functional 

## Motivation
Visual programming has some advantages, but so does plain code. My goal was to bring scripting as close to Bifrost as I could. The vnn commands are clunky but so far the only way to modify Bifrost Graphs in Maya. This language is at times still very clunky

## Installation
Extract BSL folder into your your ~/maya folder. Open Maya 2024 or Maya 2025 with Bifrost 2.12.0.0. In a new scene, run `import BSL;BSL.collect_nodes_and_types()`. Once the process is done, close and reopen Maya. Run `import BSL;BSL.ui.show()` to bring up the editor. Click the help button `?` and go through the syntax chapters to get an understanding of the language.

## The code
As mentioned above, until recently, I did not intend to make this public. The code itself here is not the feature since there is no public API. I am using `PLY` for parsing my own grammar (`res/grammar.y` and `_grammar.py`) and I am creating an AST through the `_visitor_ast.py` and `_bifast/`. That AST can then be executed as vnn commands in a Maya session. XML and JSON are planned but not currently supported. The biggest mess came about when building (and maintaining) the type resolution system (`_type.py` and `_overlord.py`). Since I did not want to rely on Bifrost itself for that, for both performance and dependency reasons, I had to write my own. It's messy, clunky, only kinda works, and most definitely not my proudest work. Oooone day, this is all gonna get rewritten nicely :)
