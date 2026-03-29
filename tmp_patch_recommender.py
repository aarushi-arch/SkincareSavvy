from pathlib import Path
p = Path('c:/Users/Hp/Desktop/SkincareSavvy/recommendations/recommender_engine.py')
text = p.read_text(encoding='utf-8')
old = '''        recommendations.append(
            {
                "name": row.get("product_name", ""),
                "brand": row.get("brand", ""),
                "type": row.get("product_type", ""),
                "concern": row.get("notable_effects", ""),
                "price": row.get("price", ""),
                "description": row.get("description", ""),
                "ingredients": row.get("clean_ingreds", ""),
                "active_ingredients": active_ingredients,
                "image_url": row.get("image_url", ""),
                "link": row.get("product_href", ""),
                "score": float(row.get("score", 0)),
                **allergy_info  # Include allergy warning info
            }
        )'''
new = '''        recommendations.append(
            {
                "name": row.get("product_name", ""),
                "brand": row.get("brand", ""),
                "type": row.get("product_type", ""),
                "concern": row.get("notable_effects", ""),
                "price": row.get("price", ""),
                "description": row.get("description", ""),
                "ingredients": row.get("clean_ingreds", ""),
                "active_ingredients": active_ingredients,
                "image_url": row.get("image_url", ""),
                "rating": row.get("rating", None),
                "link": row.get("product_href", ""),
                "score": float(row.get("score", 0)),
                **allergy_info  # Include allergy warning info
            }
        )'''
if old not in text:
    raise ValueError('pattern not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
print('done')
