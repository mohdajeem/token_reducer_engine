#!/usr/bin/env python3
"""
SEMANTIC MATCH EXTRACTOR - FIXED VERSION
This version fixes Unicode errors and properly extracts matches.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from language_config import LanguageManager
from semantic_core.semantic_match import SemanticMatch
from semantic_core.match_classifier import classify_match
from tree_sitter import QueryCursor

def normalize_route_arguments(nodes, served_method_node=None):
    call_node = None
    if served_method_node:
        current = served_method_node
        while current:
            if current.type == 'call_expression':
                call_node = current
                break
            current = current.parent
            
    if not call_node:
        for node in nodes:
            current = node
            while current:
                if current.type == 'call_expression':
                    call_node = current
                    break
                current = current.parent
            if call_node:
                break
    
    if call_node:
        arguments_child = None
        for child in call_node.children:
            if child.type == 'arguments':
                arguments_child = child
                break
        
        if arguments_child:
            arguments = []
            for child in arguments_child.named_children:
                #print(child.type,"|",child)
                if not child.type == 'string':
                    arguments.append(child.text.decode("utf-8"))

            if arguments:
                #print("arguments extracted in normalize_route_arguments:",arguments)
                return arguments
    
    return None


def normalize_call_expression(nodes):
    call_node = None

    for node in nodes:
        current = node

        while current:
            if current.type == "call_expression":
                call_node = current
                break

            current = current.parent

        if call_node:
            break

    if call_node:
        return {
            "call.start": call_node.start_byte,
            "call.end": call_node.end_byte
        }

    return None

def safe_extract_semantic_matches(matches, file_path, tree):
    """
    Extracts and classifies raw Tree-sitter query match captures into strongly-typed 
    SemanticMatch blocks while checking ranges to drop duplicate CALL matches.
    
    Args:
        matches (List[Tuple]): List of raw match capture IDs and node maps returned by Tree-sitter.
        file_path (str): The absolute path of the parsed source file.
        tree (Tree): The Tree-sitter parsed AST tree object.
        
    Returns:
        List[SemanticMatch]: A list of clean, scope-resolved SemanticMatch objects.
    """
    semantic_matches = []
    seen_calls = set()
    
    if not matches:
        return semantic_matches
    
    try:
        for idx, (match_id, match_dict) in enumerate(matches):
            try:
                capture_dict = {}
                raw_nodes = []
                
                # Extract captures
                served_method_node = None
                for capture_name, nodes in match_dict.items():
                    if not isinstance(nodes, list):
                        nodes = [nodes]
                    
                    extracted = []
                    for node in nodes:
                        raw_nodes.append(node)
                        if capture_name == "endpoint.served_method":
                            served_method_node = node
                        try:
                            text = node.text.decode("utf-8") if isinstance(node.text, bytes) else str(node.text)
                        except:
                            text = ""
                        extracted.append(text)
                    
                    if len(extracted) == 1:
                        capture_dict[capture_name] = extracted[0]
                    else:
                        capture_dict[capture_name] = extracted
                
                # Classify match
                ##print("\nMATCH RAW")
                ##print(capture_dict)
                match_type = classify_match(capture_dict.keys())
                

                if not raw_nodes:
                    continue
                
                # Create semantic match
                identity_node = raw_nodes[0]
                arguments = normalize_route_arguments(raw_nodes, served_method_node)
                # if arguments:
                #     capture_dict["route.arguments"] = arguments
                if(match_type == "ROUTE"):
                    ##print("match_type is route")
                    arguments = normalize_route_arguments(raw_nodes, served_method_node)
                    if arguments:
                        capture_dict["route.arguments"] = arguments
                
                if match_type == "CALL":

                    call_info = normalize_call_expression(raw_nodes)

                    if call_info:

                        capture_dict["call.start"] = (
                            call_info["call.start"]
                        )

                        capture_dict["call.end"] = (
                            call_info["call.end"]
                        )
                    
                    call_key = (
                        capture_dict.get("call.start", identity_node.start_byte),
                        capture_dict.get("call.end", identity_node.end_byte)
                    )
                    if call_key in seen_calls:
                        print(f"⚠️ [DEDUPLICATE CALL] Dropped duplicate CALL match for {capture_dict.get('call.func_name')} at range {call_key}")
                        continue
                    seen_calls.add(call_key)

                # if match_type == "CALL_ARGUMENTS":
                    ##print("\nFOUND CALL ARG")
                    ##print(capture_dict)

                if match_type == "CALL_ARGUMENTS":

                    call_info = normalize_call_expression(raw_nodes)

                    if call_info:

                        capture_dict["call.start"] = (
                            call_info["call.start"]
                        )

                        capture_dict["call.end"] = (
                            call_info["call.end"]
                        )
                
                # # #print("raw_nodes:\n",raw_nodes)
                # #print("INSIDE MATCH EXTRACTOR FIXED(identity_node):\n",identity_node)
                
                # #print("\nINSIDE MATCH EXTRACTOR FIXED:")

                #print("CAPTURE_DICT\n:",capture_dict)

                if match_type in {"CALL", "CALL_ARGUMENTS", "RETURN_VALUE", "FUNCTION_PARAMS"}:
                    from pathlib import Path
                    print(f"🔍 [EXTRACTED {match_type}] File: {Path(file_path).name}, Range: {identity_node.start_byte}-{identity_node.end_byte}, captures: {capture_dict}")

                semantic_match = SemanticMatch(
                    match_type=match_type,
                    captures=capture_dict,
                    file_path=file_path,
                    owner_function=None,
                    scope_id="GLOBAL",
                    start_byte=identity_node.start_byte,
                    end_byte=identity_node.end_byte,
                    start_point=identity_node.start_point,
                    end_point=identity_node.end_point
                )
                # #print("semantic_match:",semantic_match)
                
                semantic_matches.append(semantic_match)
                
            except Exception as e:
                # Skip problematic matches
                pass
        
        # ==================================================
        # POST-PROCESS: ASSIGN OWNER FUNCTIONS
        # ==================================================
        function_scopes = []
        for sm in semantic_matches:
            if sm.match_type == "FUNCTION_DEF":
                func_name = sm.captures.get("function.name")
                if func_name:
                    function_scopes.append({
                        "name": func_name,
                        "start": sm.start_byte,
                        "end": sm.end_byte
                    })
        
        # Sort by start byte so inner functions come first if we want, 
        # but usually we want the most immediate parent.
        # Actually, for nested functions, the smallest range that contains the match is the right one.
        for sm in semantic_matches:
            if sm.match_type != "FUNCTION_DEF":
                best_fit = None
                best_size = float('inf')
                
                for scope in function_scopes:
                    if scope["start"] <= sm.start_byte and sm.end_byte <= scope["end"]:
                        size = scope["end"] - scope["start"]
                        if size < best_size:
                            best_size = size
                            best_fit = scope["name"]
                
                if best_fit:
                    sm.owner_function = best_fit

        return semantic_matches
        
    except Exception as e:
        print(f"[ERROR] Extracting matches: {e}")
        return []


# For backward compatibility
extract_semantic_matches = safe_extract_semantic_matches
