import google.generativeai as genai
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

class CVEvaluator:
    def __init__(self, api_key=None, temperature=0.3):
        """Inicializē CV vērtētāju ar Gemini API"""
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("Google API atslēga nav norādīta")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.temperature = temperature
        
    def read_file(self, file_path):
        """Nolasa teksta failu"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Kļūda: Fails {file_path} nav atrasts")
            return None
        except Exception as e:
            print(f"Kļūda lasot failu {file_path}: {e}")
            return None
    
    def create_prompt(self, jd_text, cv_text):
        """Izveido promptu CV novērtēšanai"""
        prompt = f"""
## Uzdevums: CV un darba apraksta atbilstības novērtēšana

Kā pieredzējis HR speciālists, analizē šo darba aprakstu un kandidāta CV, lai sniegtu objektīvu novērtējumu.

### DARBA APRAKSTS:
{jd_text}

### KANDIDĀTA CV:
{cv_text}

### NOVĒRTĒJUMA KRITĒRIJI:

1. **Atbilstības vērtējums (0-100)**: Cik procentos CV atbilst darba apraksta prasībām
2. **Kopsavilkums**: Īss apraksts par atbilstības līmeni
3. **Stiprās puses**: Galvenās prasmes un pieredze, kas atbilst darba aprakstam
4. **Trūkstošās prasības**: Svarīgas prasmes no darba apraksta, kas nav atrodamas CV
5. **Ieteikums**: "strong match" | "possible match" | "not a match"

### ATBILDES FORMATS (tikai JSON):
{{
  "match_score": 0-100,
  "summary": "Īss apraksts, cik labi CV atbilst JD",
  "strengths": [
    "Galvenās prasmes/pieredze no CV, kas atbilst JD"
  ],
  "missing_requirements": [
    "Svarīgas JD prasības, kas CV nav redzamas"
  ],
  "verdict": "strong match | possible match | not a match"
}}

Atgriezt TIKAI JSON formātu, bez papildu teksta vai komentāriem.
"""
        return prompt
    
    def save_prompt_to_file(self, prompt, filename="prompt.md"):
        """Saglabā promptu failā"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Prompt saglabāts kā: {filename}")
    
    def extract_json_from_response(self, text):
        """Izvelk JSON no atbildes teksta"""
        try:
            # Mēģina atrast JSON objektu tekstā
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Ja neatrod JSON, mēģina parsēt visu tekstu
                return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Kļūda JSON parsēšanā: {e}")
            print(f"Atbilde: {text}")
            return None
    
    def evaluate_cv(self, jd_text, cv_text, cv_number):
        """Novērtē viena CV atbilstību darba aprakstam"""
        print(f"Novērtē CV {cv_number}...")
        
        # Izveido promptu
        prompt = self.create_prompt(jd_text, cv_text)
        self.save_prompt_to_file(prompt, f"prompt_cv{cv_number}.md")
        
        try:
            # Izsauc Gemini API
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature
                )
            )
            
            # Apstrādā atbildi
            if response.text:
                result = self.extract_json_from_response(response.text)
                if result:
                    return result
                else:
                    print("Neizdevās iegūt JSON no atbildes")
                    return None
            else:
                print("Saņemta tukša atbilde")
                return None
                
        except Exception as e:
            print(f"Kļūda Gemini API izsaukšanā: {e}")
            return None
    
    def save_json_result(self, result, cv_number):
        """Saglabā JSON rezultātu"""
        os.makedirs("outputs", exist_ok=True)
        filename = f"outputs/cv{cv_number}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"JSON rezultāts saglabāts kā: {filename}")
        return filename
    
    def generate_report(self, result, cv_number, format='md'):
        """Ģenerē pārskatu no JSON rezultātiem"""
        if format == 'md':
            return self._generate_markdown_report(result, cv_number)
        elif format == 'html':
            return self._generate_html_report(result, cv_number)
        else:
            return self._generate_markdown_report(result, cv_number)
    
    def _generate_markdown_report(self, result, cv_number):
        """Ģenerē Markdown pārskatu"""
        # Pārbauda, vai ir dati
        if not result:
            return f"# CV {cv_number} Novērtējuma Pārskats\n\n**Kļūda:** Neizdevās ģenerēt novērtējumu"
        
        strengths = result.get('strengths', [])
        missing = result.get('missing_requirements', [])
        
        report = f"""# CV {cv_number} Novērtējuma Pārskats

## Atbilstības Rezultāts

**Vērtējums:** {result.get('match_score', 'N/A')}/100  
**Ieteikums:** {result.get('verdict', 'N/A')}

## Kopsavilkums
{result.get('summary', 'Nav pieejams')}

## Stiprās Puses
{chr(10).join('- ' + strength for strength in strengths) if strengths else '- Nav identificētu stipro pusi'}

## Trūkstošās Prasības
{chr(10).join('- ' + requirement for requirement in missing) if missing else '- Visas galvenās prasības ir apmierinātas'}

---
*Ģenerēts ar AI CV vērtētāju*
"""
        return report
    
    def _generate_html_report(self, result, cv_number):
        """Ģenerē HTML pārskatu"""
        if not result:
            return "<html><body><h1>Kļūda: Neizdevās ģenerēt novērtējumu</h1></body></html>"
        
        strengths = result.get('strengths', [])
        missing = result.get('missing_requirements', [])
        
        strengths_html = "".join(f"<li>{strength}</li>" for strength in strengths) if strengths else "<li>Nav identificētu stipro pusi</li>"
        missing_html = "".join(f"<li>{requirement}</li>" for requirement in missing) if missing else "<li>Visas galvenās prasības ir apmierinātas</li>"
        
        # Noteikt krāsu pēc verdict
        verdict_color = {
            "strong match": "#28a745",
            "possible match": "#ffc107", 
            "not a match": "#dc3545"
        }.get(result.get('verdict', ''), "#6c757d")
        
        report = f"""<!DOCTYPE html>
<html lang="lv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CV {cv_number} Novērtējums</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        .score {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .verdict {{ padding: 5px 10px; border-radius: 5px; display: inline-block; color: white; }}
        .section {{ margin-bottom: 30px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CV {cv_number} Novērtējuma Pārskats</h1>
        <div class="score">{result.get('match_score', 'N/A')}/100</div>
        <div class="verdict" style="background-color: {verdict_color};">{result.get('verdict', 'N/A')}</div>
    </div>
    
    <div class="section">
        <h2>Kopsavilkums</h2>
        <p>{result.get('summary', 'Nav pieejams')}</p>
    </div>
    
    <div class="section">
        <h2>Stiprās Puses</h2>
        <ul>{strengths_html}</ul>
    </div>
    
    <div class="section">
        <h2>Trūkstošās Prasības</h2>
        <ul>{missing_html}</ul>
    </div>
    
    <div class="footer">
        <p>Ģenerēts ar AI CV vērtētāju</p>
    </div>
</body>
</html>"""
        return report
    
    def save_report(self, report, cv_number, format='md'):
        """Saglabā pārskatu failā"""
        os.makedirs("outputs", exist_ok=True)
        extension = 'md' if format == 'md' else 'html'
        filename = f"outputs/cv{cv_number}_report.{extension}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Pārskats saglabāts kā: {filename}")

def create_sample_files():
    """Izveido parauga failus, ja tie neeksistē"""
    os.makedirs("sample_inputs", exist_ok=True)
    
    # Darba apraksts
    if not os.path.exists("sample_inputs/jd.txt"):
        jd_content = """Mēs meklējam pieredzējušu Python izstrādātāju ar vismaz 3 gadu pieredzi web izstrādē. 

Prasības:
- Python programmēšanas pieredze
- Zināšanas Django vai Flask ietvaros
- Datu bāzu pieredze (SQL, PostgreSQL)
- API izstrādes pieredze
- Git versiju kontroles sistēma
- Angļu valodas zināšanas

Vēlamās prasmes:
- React vai Vue.js
- Docker pieredze
- AWS vai citu mākoņu pakalpojumu pieredze
- Testēšanas automatizācija

Atbildības:
- Web lietotņu izstrāde un uzturēšana
- API izstrāde
- Datu bāzu dizains un optimizācija
- Sadarbība ar komandu"""
        
        with open("sample_inputs/jd.txt", "w", encoding="utf-8") as f:
            f.write(jd_content)
        print("Izveidots sample_inputs/jd.txt")
    
    # CV 1 - labs kandidāts
    if not os.path.exists("sample_inputs/cv1.txt"):
        cv1_content = """Jānis Bērziņš
Python izstrādātājs

Pieredze:
Senior Python Developer, Tech Company (2020-pašlaik)
- Izstrādāju web lietotnes, izmantojot Django un Flask
- Veicu API izstrādi REST principos
- Strādāju ar PostgreSQL un MongoDB
- Izmantoju Git versiju kontroles sistēmu
- Automatizēju testēšanu ar pytest

Prasmes:
- Python, Django, Flask
- SQL, PostgreSQL, MongoDB
- REST API, GraphQL
- Git, Docker, AWS
- React (pamatzināšanas)
- Angļu valoda (tekoši)

Izglītība:
Datorzinātnes bakalaurs, Latvijas Universitāte"""
        
        with open("sample_inputs/cv1.txt", "w", encoding="utf-8") as f:
            f.write(cv1_content)
        print("Izveidots sample_inputs/cv1.txt")
    
    # CV 2 - vidējs kandidāts
    if not os.path.exists("sample_inputs/cv2.txt"):
        cv2_content = """Anna Liepiņa
Junior Python izstrādātāja

Pieredze:
Python Developer, Startup Company (2022-pašlaik)
- Izstrādāju web lietotnes ar Flask
- Veicu vienkāršu API izstrādi
- Strādāju ar SQLite datu bāzēm
- Pamata Git lietošana

Prasmes:
- Python, Flask
- SQLite
- REST API pamati
- Git pamati
- Angļu valoda (vidēji)

Izglītība:
Datorzinātnes bakalaurs, Rīgas Tehniskā universitāte"""
        
        with open("sample_inputs/cv2.txt", "w", encoding="utf-8") as f:
            f.write(cv2_content)
        print("Izveidots sample_inputs/cv2.txt")
    
    # CV 3 - vājš kandidāts
    if not os.path.exists("sample_inputs/cv3.txt"):
        cv3_content = """Pēteris Ozoliņš
Front-end izstrādātājs

Pieredze:
Web Developer, Digital Agency (2021-pašlaik)
- Izstrādāju lietotņu front-end daļu ar React
- Veicu UI/UX dizainu
- Strādāju ar JavaScript, HTML, CSS

Prasmes:
- JavaScript, React, HTML, CSS
- UI/UX dizains
- Git
- Angļu valoda (tekoši)

Izglītība:
Dizains un māksla, Mākslas akadēmija"""
        
        with open("sample_inputs/cv3.txt", "w", encoding="utf-8") as f:
            f.write(cv3_content)
        print("Izveidots sample_inputs/cv3.txt")

def main():
    """Galvenā izpildes funkcija"""
    
    # Izveido parauga failus
    create_sample_files()
    
    try:
        # Inicializēt vērtētāju (izmanto vidi mainīgo)
        evaluator = CVEvaluator()
        
        # Nolasīt darba aprakstu
        jd_text = evaluator.read_file("sample_inputs/jd.txt")
        if not jd_text:
            print("Neizdevās nolasīt darba aprakstu")
            return
        
        # Novērtēt katru CV
        for i in range(1, 4):
            cv_text = evaluator.read_file(f"sample_inputs/cv{i}.txt")
            if cv_text:
                print(f"\n=== APSTRĀDĀ CV {i} ===")
                
                # Novērtēt CV
                result = evaluator.evaluate_cv(jd_text, cv_text, i)
                
                if result:
                    # Saglabāt JSON rezultātu
                    evaluator.save_json_result(result, i)
                    
                    # Ģenerēt un saglabāt pārskatus
                    md_report = evaluator.generate_report(result, i, 'md')
                    evaluator.save_report(md_report, i, 'md')
                    
                    html_report = evaluator.generate_report(result, i, 'html')
                    evaluator.save_report(html_report, i, 'html')
                    
                    print(f"CV {i} novērtēšana pabeigta!")
                else:
                    print(f"Neizdevās novērtēt CV {i}")
            else:
                print(f"Neizdevās nolasīt CV {i}")
                
    except ValueError as e:
        print(f"Konfigurācijas kļūda: {e}")
        print("Lūdzu iestatiet GOOGLE_API_KEY vidi mainīgo vai .env failā")
    except Exception as e:
        print(f"Negaidīta kļūda: {e}")

if __name__ == "__main__":
    main()
