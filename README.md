# mcpmoose
MCP testing for the MOOSE framework

## Create objects database
```bash
myapp-opt --json > syntax_full.inp
sed '1,/^\*\*START JSON DATA\*\*$/d' syntax_full.inp \
  | sed '/^\*\*END JSON DATA\*\*$/d' \
  > syntax_full.json
python scripts/make_objects.py
```
