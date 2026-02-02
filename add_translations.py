import json
from deep_translator import GoogleTranslator
import time

def add_translations(input_file, output_file):
    """JSON 파일의 모든 예문에 한글 번역 추가"""
    print(f"Loading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        words = json.load(f)
    
    translator = GoogleTranslator(source='en', target='ko')
    total = len(words)
    
    print(f"Total words to process: {total}")
    
    for idx, word in enumerate(words, 1):
        # 이미 번역이 있으면 건너뛰기
        if 'example_kr' in word and word['example_kr']:
            print(f"[{idx}/{total}] Skipping {word['word']} (already has translation)")
            continue
        
        if 'example' in word and word['example']:
            try:
                # 번역 실행
                translation = translator.translate(word['example'])
                word['example_kr'] = translation
                print(f"[{idx}/{total}] {word['word']}: {word['example']} → {translation}")
                
                # API 제한 방지를 위한 딜레이
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[{idx}/{total}] Error translating {word['word']}: {e}")
                word['example_kr'] = ""
        else:
            word['example_kr'] = ""
    
    # 결과 저장
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    add_translations(
        'static/data/english_words.json',
        'static/data/english_words.json'
    )
