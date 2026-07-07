

<!-- first build_graph() function -->
==============================================
semantic_graph => making (initializing)
pass it to CaptureProcessor(semantic_graph)

declare a variable registry => SemanticRegistry()

--------------- WHAT ALL THESE DO --------------------
************** 1. SemanticGraph **********************
SemanticGraph() => a class:
initialize the graph => imports, calls, routes_in ... contracts => all are defaultdict(list) type

and there all functions => add_import, add_call ... etc

and in the end an export function who export the graph all initialized variables in dict form

*************** 2. CaptureProcess ********************
we pass semantic_graph into this, initialize graph,
and then handlres = {import.source : self.handle_import, ...}
attach function name with these handlers 

its all function add event.capture_name into .type with file_name, with event.text, event.other parts

but we didn't call it in our function

*************** 3. SemanticRegistry **********************

it intialize itself, and 
self.all_matches = [] an empty array

contains two function 
1. add_matches(matches) 
2. get_matches_by_type(match_type)

*********************************************************END

now iterating on directory,

tree = parse kiya
query run ki

matches banaya 
import this => from semantic_core.match_extractor_fixed import safe_extract_semantic_matches

use this 
safe_extract_sematic_matches(matches, rel_path, tree)

in end we add its result into registry 

****************** 4 ***********************************




==============================================