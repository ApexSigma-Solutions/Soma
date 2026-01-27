#!/bin/bash
export NEO4J_URI=bolt://localhost:7687
cd /d/projects/Omega_KG_dev
"C:/Users/steyn/AppData/Roaming/Python/Scripts/poetry" run capture-server
