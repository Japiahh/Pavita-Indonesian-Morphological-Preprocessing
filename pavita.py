import json
import os
import traceback

from modules.tokenizer.chakaria import ChakariaTokenizer
from modules.postag.erisa import ErisaPOSTagger
from modules.parser.syntactic.zhyanisintatic import ZhyaniSyntacticParser
from modules.parser.depedency.zhyanidepedency import ZhyaniDependencyParser
    
from utils.sasmita import SasmitaTagChecker

class PavitaMSP:
    """
    Pavita (Purified/Refined) MSP Pipeline.
    """
    def __init__(self, config=None):
        print("\n--- Initializing Pavita MSP Engine ---")
        self.config = {
            'use_tagger': True,
            'use_checker': True,
            'use_syntactic': True,
            'use_dependency': True
        }
        if config: self.config.update(config)
        
        # Inisialisasi Modul
        self.tokenizer = ChakariaTokenizer()
        self.tagger = ErisaPOSTagger() if self.config['use_tagger'] else None
        self.tag_checker = SasmitaTagChecker() if (self.config['use_tagger'] and self.config['use_checker']) else None
        self.syn_parser = ZhyaniSyntacticParser() if self.config['use_syntactic'] else None
        self.dep_parser = ZhyaniDependencyParser() if self.config['use_dependency'] else None
        
        print("--- Engine Ready ---\n")

    def purify_sentence(self, text):
        """
        Memproses satu kalimat.
        """
        try:
            # 1. Tokenizing
            raw_tokens = self.tokenizer.tokenize(text)
            
            # 2. Tagging & Merging
            if self.tagger:
                tagged_output = self.tagger.posttag(raw_tokens)
                # Ambil token yang sudah di-merge dari hasil tagging
                final_tokens = [t[0] for t in tagged_output]
            else:
                tagged_output = []
                final_tokens = raw_tokens

            # 2.5 Sasmita Check
            if self.tag_checker and tagged_output:
                self.tag_checker.check_and_collect(tagged_output)

            # 3. Syntactic Parsing
            syntax_tree_output = []
            if self.syn_parser and tagged_output:
                syntax_tree_output = self.syn_parser.syntactic_parse(tagged_output)

            # 4. Dependency Parsing
            dep_graph_output = []
            if self.dep_parser and syntax_tree_output:
                raw_dep_graph = self.dep_parser.dependency_parse(syntax_tree_output)
                
                # --- FILTERING PENTING ---
                # Hapus hasil dependensi yang kosong (text length 0)
                # Ini memperbaiki bug "sentence_id: 2" dengan text ""
                if isinstance(raw_dep_graph, list):
                    for dep in raw_dep_graph:
                        if isinstance(dep, dict) and dep.get("text", "").strip():
                            dep_graph_output.append(dep)
                else:
                    dep_graph_output = raw_dep_graph

            # Susun Result Sesuai Template
            result = {
                "raw_text": text,
                "token": final_tokens,
                "tagged": tagged_output,
                "syntax_tree": syntax_tree_output,
                "dependency_graph": dep_graph_output
            }

            return result

        except Exception as e:
            print(f"[Error Processing]: {text[:20]}... -> {e}")
            traceback.print_exc()
            return None

    def process_file(self, input_filepath, output_filepath=None):
        if not os.path.exists(input_filepath):
            print(f"[Error] File {input_filepath} tidak ditemukan.")
            return

        results = []
        print(f"Membaca: {input_filepath}")
        
        with open(input_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        for i, line in enumerate(lines):
            clean_line = line.strip()
            if not clean_line: continue

            out = self.purify_sentence(clean_line)
            if out: results.append(out)
            
            if (i+1) % 10 == 0: print(f"Processing {i+1}/{total}...")

        if self.tag_checker:
            self.tag_checker.save_report()

        if output_filepath:
            print(f"Menyimpan JSON ke: {output_filepath}")
            with open(output_filepath, 'w', encoding='utf-8') as f:
                # ensure_ascii=False agar huruf terbaca normal
                # indent=4 agar rapi
                json.dump(results, f, indent=4, ensure_ascii=False)
            print("Selesai.")

# --- Run ---
if __name__ == "__main__":
    OUTPUT_FOLDER = "result"
    if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)

    pavita = PavitaMSP()
    
    # Pastikan nama file input sesuai
    pavita.process_file("output_clean.txt", os.path.join(OUTPUT_FOLDER, "pavita_result.json"))