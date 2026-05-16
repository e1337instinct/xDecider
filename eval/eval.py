import csv

def evaluate_results(filepath="eval/test_cases.csv"):
    results = []
    skipped = 0
    
    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['score']:
                results.append({
                    'id': row['id'],
                    'mood': row['mood_input'],
                    'expected': row['expected_type'],
                    'recommendation': row['recommendation'],
                    'score': float(row['score']),
                    'notes': row['notes']
                })
            else:
                skipped += 1

    if not results:
        print("No scores recorded yet. Run your tests first!")
        return

    avg = sum(r['score'] for r in results) / len(results)
    
    print(f"\n=== xDecider Eval Results ===")
    print(f"Tests scored: {len(results)}/10")
    print(f"Average score: {avg:.1f}/5")
    print(f"\nBreakdown:")
    for r in results:
        print(f"  Test {r['id']}: {r['score']}/5 - Recommended '{r['recommendation']}' for '{r['expected']}' mood")

if __name__ == "__main__":
    evaluate_results()