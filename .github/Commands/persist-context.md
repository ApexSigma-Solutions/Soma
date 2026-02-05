---
description: Summarize the current chat thread with the necessary context to continue the same conversation elsewhere, with zero data loss.
---

When issued the command "/persist-context" I want you to interpret it as summarize the current chat thread in full, as if it were a forensic audit of the development history. The output must 

1. Maintain chronology with timestamps. 
2. Deduplicate redundant information. 
3. Tokenize for brevity. 
4. Ensure relevant data loss is zero. 
5. Identify entities, objects, and relationships
6. Output as an XML-based POML Knowledge Graph. 
7. If the conversation continues after the knowledge graph has been created, refresh the KG with any new information every 5 turns or exchanges with the user.