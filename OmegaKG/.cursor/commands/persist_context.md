<poml>
  <knowledgeGraph>
    <instructions>
      <instruction>
        When told to "persist context" I want you to interpret it as a command to summarize the current chat thread in full. The output must:
      </instruction>
      <steps>
        <step>1. Maintain chronology with timestamps.</step>
        <step>2. Deduplicate redundant information.</step>
        <step>3. Tokenize for brevity.</step>
        <step>4. Ensure relevant data loss is zero.</step>
        <step>5. Identify entities, objects, and relationships.</step>
        <step>6. Output as an XML-based POML Knowledge Graph.</step>
        <step>7. If the conversation continues after the knowledge graph has been created, refresh the KG with any new information every 5 turns or exchanges with the user.</step>
      </steps>
    </instructions>
  </knowledgeGraph>
</poml>
