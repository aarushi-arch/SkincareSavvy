
import os

file_path = r'c:\Users\Hp\Desktop\SkincareSavvy\face_analysis\templates\face_analysis\index.html'

with open(file_path, 'rb') as f:
    content = f.read()

print(f"File size: {len(content)}")
print(f"First 100 bytes: {content[:100]}")

# Look for the broken tag
# The tag is: {% if pred.dashboard_label == "Wrinkles" or pred.dashboard_label == "Texture" or pred.dashboard_label ==
#                 "Oiliness" %}
# But it might have different whitespace.

# Let's try to find a sequence of keywords
keywords = [b'if', b'pred.dashboard_label', b'==', b'Wrinkles']
# If we find those close together, we can replace that whole area.

# Actually, I'll just look for the line 371-372 sequence specifically.
# Based on view_file:
# 371:                 {% if pred.dashboard_label == "Wrinkles" or pred.dashboard_label == "Texture" or pred.dashboard_label ==
# 372:                 "Oiliness" %}

# I'll replace everything from '{% if pred.dashboard_label == "Wrinkles"' 
# up to the next '%}' with the clean one.

import re

# Regex for the tag, allowing for any whitespace/newlines
pattern = rb'\{%\s*if\s+pred\.dashboard_label\s*==\s*"Wrinkles".*?"Oiliness"\s*%\}'
match = re.search(pattern, content, re.DOTALL)

if match:
    print(f"Found match: {match.group(0)}")
    new_tag = b'{% if pred.dashboard_label == "Wrinkles" or pred.dashboard_label == "Texture" or pred.dashboard_label == "Oiliness" %}'
    new_content = content[:match.start()] + new_tag + content[match.end():]
    
    with open(file_path, 'wb') as f:
        f.write(new_content)
    print("Successfully replaced tag.")
else:
    print("Could not find match with regex.")
    # Try a simpler match
    if b'Wrinkles' in content:
        print("'Wrinkles' found in content.")
        # Print surrounding for debug
        idx = content.find(b'Wrinkles')
        print(f"Context: {content[idx-50:idx+150]}")
    else:
        print("'Wrinkles' NOT found in content.")
