
def remove_duplicates(results):
    if not results:
        return [] 
    
    seen = set()
    unique_results = []
    
    for result in results:
        key = result.get('data', '').get('id', '')
        if key not in seen:
            seen.add(key)
            unique_results.append(result)
    
    return unique_results
