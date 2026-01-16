import logging
import os

from preprocessing.nlp.parser.parse_data import cfg, clause_boundary, coordination_patern, treebank
from preprocessing.nlp.parser.sintatic.module import chunking

class ZhyaniSyntacticParser:
    def __init__(self):
        """
        Inisialisasi parser dengan aturan CFG, batas klausa, pola koordinasi, dan treebank.
        """
        self.cfg = cfg
        self.clause_boundary = clause_boundary

        # Load rules from JSON files
        self.load()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)

        self.chunking = chunking.Chunking()

    def load(self, grammar_file=None, lexicon_file=None):
        """
        Memanggil file JSON yang sudah diimpor:
        1. cfg.json → cfg
        2. clause_boundary.json → clause_boundary
        3. coordination_patern.json → coordination_patern
        4. treebank.json → treebank (opsional)
        """
        pass


    def evaluate (self, test_data):
        """
        """
        pass

    def log_parse (self, message, level="INFO"):
        """
        """
        pass

#fungsi utama
    def syntactic_parse(self, tokens):
        """
        Manager Utama: Mengoordinasikan parsing dan mengembalikan struktur Pohon.
        Output: Tuple ('S', chunks) yang aman untuk Dependency Parser.
        """
        
        # LANGKAH 1: Lakukan Chunking dengan Pengaman
        # Kita pastikan chunks selalu berupa list, tidak pernah None.
        chunks = self._safe_chunking(tokens)

        # LANGKAH 2: Deteksi Klausa (Opsional, fail-safe)
        clause_boundaries = self._safe_clause_detection(tokens)

        # LANGKAH 3: Bentuk Pohon Akhir
        # Format Tuple ('S', isi) adalah standar untuk Dependency Parser & Traversing
        final_tree = ('S', chunks)

        # LANGKAH 4: Analisis Tambahan (Side Effect)
        # Menghitung constituent dan depth untuk metadata (tidak wajib untuk parsing jalan)
        self._safe_analysis(final_tree, chunks)

        # LANGKAH 5: Return Hasil
        return final_tree

    def prehandle (self, tokens):
        """
        fungsi keseluruhan handle
        """
        pass

#safety
    def _safe_chunking(self, tokens):
        """
        Worker 1: Mencoba melakukan chunking.
        Jika gagal/error, dia akan mengembalikan token asli (Raw Tokens) agar tidak crash.
        """
        try:
            # Cek apakah fungsi chunking ada
            if hasattr(self, 'pre_parse_chunking'):
                chunks = self.pre_parse_chunking(tokens)
                
                # Validasi: Hasil harus list dan tidak None
                if chunks is not None and isinstance(chunks, list):
                    return chunks
                    
        except Exception as e:
            # Uncomment baris bawah untuk debugging jika penasaran errornya apa
            # print(f"[Warning] Chunking Error: {e}")
            pass
            
        # FALLBACK: Jika chunking gagal total, kembalikan token mentah
        # Ini mencegah program berhenti, meskipun struktur pohonnya jadi datar.
        return tokens

    def _safe_clause_detection(self, tokens):
        """
        Worker 2: Mencoba mendeteksi klausa dengan aman.
        """
        try:
            if hasattr(self, 'detect_clause_boundary'):
                return self.detect_clause_boundary(tokens)
        except Exception:
            pass
        return []

    def _safe_analysis(self, tree, chunks):
        """
        Worker 3: Analisis metadata (Constituents & Depth).
        Error di sini tidak boleh mematikan parsing utama.
        """
        try:
            if hasattr(self, 'get_constituents'):
                self.get_constituents(tree)
            
            if hasattr(self, 'annotate_depth_and_level'):
                self.annotate_depth_and_level(chunks)
        except Exception:
            pass

#fungsi sintatik parsing
    def match_rule(self, lhs, rhs_labels):
        """
        Mengecek apakah 'rhs' (list of token labels seperti ['DT-DEF', 'NN-COM'])
        cocok dengan salah satu produksi dari 'lhs' dalam CFG parser.

        Matching-nya fleksibel:
        - Token label seperti 'NN-COM' akan dicocokkan dengan basis non-terminal 'NN'
        - Turunan simbol RHS boleh cocok dengan basis turunan dari LHS
        - Kalau produksi punya simbol non-terminal, akan dicek anak-anaknya jika ada
        """
        if lhs not in self.cfg_rules:
            return False

        for production in self.cfg_rules[lhs]:
            if len(production) != len(rhs_labels):
                continue

            match = True
            for expected, actual in zip(production, rhs_labels):
                if expected == actual:
                    continue
                elif expected in self.cfg_rules:
                    # Cek apakah actual adalah turunan dari expected
                    possible_tags = [item[0] for item in self.cfg_rules[expected]]
                    if actual not in possible_tags:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                return True

        return False

    def get_constituents(self, tree):
        """

        """
        if tree is None:
            return [], 0
        
        constituents = []

        def is_subtree(node):
            return isinstance(node, tuple) and len(node) > 1 and isinstance(node[1], (list, tuple)) and not isinstance(node[1], str)

        def traverse(node, pos):
            if isinstance(node, str):
                return pos + 1, 1, node

            label = node[0]
            children = node[1]
            start = pos
            total_tokens = 0
            collected_subtree = []

            for child in children:
                if isinstance(child, tuple) and isinstance(child[1], str):  # leaf token
                    collected_subtree.append((child[0], child[1]))
                    pos += 1
                    total_tokens += 1
                else:  # subtree
                    pos, child_tokens, sub = traverse(child, pos)
                    total_tokens += child_tokens
                    collected_subtree.append(sub)

            end = pos
            subtree = (label, collected_subtree)
            constituents.append((label, start, end, subtree))
            return end, total_tokens, subtree

        _, total_leaf_count, _ = traverse(tree, 0)
        return constituents, total_leaf_count

    def is_valid_structure(self, lhs, rhs_labels):
        """
        Validasi struktur berdasarkan CFG. Cuma pakai label-label aja, tanpa mikirin token-token norak itu.
        """
        if lhs not in self.cfg:
            return False

        # Filter CON-* karena mereka cuma perekat, bukan struktur sejati
        clean_labels = []
        for label in rhs_labels:
            if isinstance(label, tuple):
                label = label[0]
            if not str(label).startswith("CON-"):
                clean_labels.append(label)

        for production in self.cfg[lhs]:
            if len(production) != len(clean_labels):
                continue
            if all(
                expected == actual or str(actual).startswith(expected + "-")
                for expected, actual in zip(production, clean_labels)
            ):
                return True

        return False

    def detect_clause_boundary(self, tokens):
        """
        Deteksi batas klausa berdasarkan token POS-tagged.
        Mengembalikan list tuple: (start_idx, end_idx)
        """
        boundaries = []
        start = 0

        for i, chunk in enumerate(tokens):
            if isinstance(chunk, tuple) and isinstance(chunk[1], list):
                # Ini chunk (misalnya: ('VP', [...]))
                label = chunk[0]
                if label == 'VP' and i > start:
                    boundaries.append((start, i))
                    start = i
            else:
                # Ini token mentahan (misalnya: ('lalu', 'CON-COR'))
                token, label = chunk
                if label.startswith("CON-") and i > start:
                    boundaries.append((start, i))
                    start = i

        if start < len(tokens):
            boundaries.append((start, len(tokens)))

        return boundaries

    def pre_parse_chunking(self, tokens):
        """
        Mengelompokkan token menjadi chunk (NP, VP, dll).
        Dilengkapi try-except per item agar satu error tidak membatalkan semua chunk.
        """
        all_chunks = []
        segments = []
        buffer = []

        # Step 1: Potong segmen (Safe)
        for token in tokens:
            buffer.append(token)
            tag = token[1]
            if tag.startswith("SYM-COM") or tag.startswith("SYM-DOT") or tag.startswith("CON-"):
                segments.append(buffer)
                buffer = []
        if buffer:
            segments.append(buffer)

        # Step 2: Proses segmen
        for segment in segments:
            i = 0
            while i < len(segment):
                try:
                    # Skip jika sudah chunk
                    if isinstance(segment[i], tuple) and isinstance(segment[i][1], list):
                        all_chunks.append(segment[i])
                        i += 1
                        continue

                    token, tag = segment[i]
                    main_tag = tag.split("-")[0]
                    
                    # --- LOGIKA CHUNKING ---
                    # Kita gunakan assignment sementara untuk mencegah crash unpacking
                    chunk_result = None
                    
                    if self.chunking.is_np_token(tag) and (i == 0 or not segment[i - 1][1].startswith("IN")):
                        chunk_result = self.chunking.build_np(segment, i)

                    elif main_tag == "VB" or (tag in {"MOD-TEMP", "MOD-ACT"} and i + 1 < len(segment) and segment[i + 1][1].startswith("VB")):
                        chunk_result = self.chunking.build_vp(segment, i)

                    elif tag.startswith("IN"):
                        chunk_result = self.chunking.build_pp(segment, i)

                    elif self.chunking.is_adjp_token(tag) and not tag.startswith("MOD"):
                        chunk_result = self.chunking.build_adjp(segment, i)

                    elif self.chunking.is_advp_token(tag):
                        chunk_result = self.chunking.build_advp(segment, i)
                    
                    elif self.chunking.is_wh_token(tag):
                        chunk_result = self.chunking.build_interrog(segment, i)

                    # --- PROSES HASIL ---
                    if chunk_result:
                        chunk, new_i = chunk_result
                        all_chunks.append(chunk)
                        i = new_i
                    else:
                        # Handle token simpel/manual
                        if main_tag == "CON":
                            all_chunks.append(('CONJ', [segment[i]]))
                            i += 1
                        elif main_tag == "INT":
                            all_chunks.append(('INTJ', [segment[i]]))
                            i += 1
                        elif main_tag == "SYM":
                            all_chunks.append(('PUNCT', [segment[i]]))
                            i += 1
                        else:
                            # Token tidak ter-chunk, masukkan sebagai raw token
                            all_chunks.append(segment[i])
                            i += 1

                except Exception as e:
                    # Jika satu chunk gagal, lewati token ini saja, jangan crash semuanya
                    # print(f"Error processing token {i}: {e}")
                    # Masukkan token bermasalah sebagai raw token agar data tidak hilang
                    if i < len(segment):
                        all_chunks.append(segment[i])
                    i += 1

        return all_chunks
    
    def annotate_depth_and_level(self, chunks, current_depth=0, sentence=1, parent=None):
        """
        Rekursif annotate depth dan level dari setiap chunk.
        - depth: seberapa dalam nestednya.
        - level: seberapa jauh dari root kalimat.
        """
        annotated = []

        for chunk in chunks:
            if isinstance(chunk, tuple):
                label, content = chunk

                if isinstance(content, list):
                    # Ini parent, masuk lebih dalam
                    annotated.append({
                        "sentence": sentence,
                        "depth": current_depth,
                        "label": label,
                        "parent": parent,
                        "content": content
                    })

                    # Rekursif ke anak-anaknya
                    child_annotated = self.annotate_depth_and_level(content, current_depth + 1, sentence + 1, label)
                    annotated.extend(child_annotated)
                else:
                    # Skip leaf token, gak usah masukin ke depth_info
                    continue

        return annotated

#handle CONJ
    def handle_coordination() :
        """
        """
        pass

    def handle_reordering():
        """
        """
        pass

    def handle_parenthesis() :
        """
        """
        pass

    def handle_conjunction_scope() :
        """
        """
        pass

    def handle_apposition() :
        """
        """
        pass

    def handle_inversion() :
        """
        """
        pass

    def handle_coordination (self) :
        """
        """
        pass

    def handle_reordering (self) :
        """
        """
        pass
    
    def handle_punctuation_scope (self) :
        """
        """
        pass

    def handle_quote_scope(sentence):
        """
        """
        pass

class ppront:
    @staticmethod
    def pretty_print_to_file(parse_result, output_txt_path):
        def pretty(chunk, indent=0):
            tab = "    "  # 4 spasi, biar matching sama tab dari contohmu

            if isinstance(chunk, tuple) and isinstance(chunk[1], list):
                # Awal parent
                s = f"{tab * indent}('{chunk[0]}', [\n"
                for c in chunk[1]:
                    s += pretty(c, indent + 1) + ",\n"
                s += f"{tab * indent}])"
                return s
            elif isinstance(chunk, tuple):
                return f"{tab * indent}{repr(chunk)}"
            else:
                return f"{tab * indent}{str(chunk)}"

        try:
            os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
            with open(output_txt_path, "w", encoding="utf-8") as f:
                for chunk in parse_result:
                    f.write(pretty(chunk) + "\n")
            print(f"[RISA NYOLY UPDATE] File udah disimpan rapi di:\n>> {os.path.abspath(output_txt_path)}\nHebat, kamu berhasil... sekali seumur hidup.")
        except FileNotFoundError:
            print(f"[RISA PANIK] File '{output_txt_path}' gak bisa dibuat. Folder-nya bener gak tuh? Cek dulu, jangan cuma bengong.")
        except Exception as e:
            print(f"[RISA ERROR] Nih ya, errornya: {e}\nFix kamu ngerusak sesuatu tanpa sadar.")

if __name__ == "__main__":
    parser = ZhyaniSyntacticParser()
    # parser.load() # Uncomment jika load logic sudah benar

    tokens = [
        ("Dia", "PRP-PER"),
        ("duduk", "VB-ACT"),
        ("di", "IN-LOC"),
        ("sebuah", "DT-DEF"),
        ("kelapa", "NN-COM"),
        (",", "SYM-COM"),
        ("lalu", "CON-COR"),
        ("memakannya", "VB-ACT"),
        ("sambil", "MOD-TEMP"),
        ("tersenyum", "VB-ACT"),
        ("lembut", "ADV-ATT"),
        (".", "SYM-DOT"),
        ("meskipun", "CON-SUB"),
        ("warna", "NN-COM"),
        ("kelapa", "NN-COM"),
        ("itu", "DT-DEF"),
        ("aneh", "JJ-QUALITY"),
        (".", "SYM-DOT"),
        ("padahal", "CON-SUB"),
        ("kau", "PRP-PER"),
        ("tahu", "VB-STAT"),
        ("jawabannya", "NN-COM"),
        ("sejak", "IN-TEMP"),
        ("tadi", "MOD-TEMP"),
        (",", "SYM-COM"),
        ("kan", "MOD-DISC"),
        ("?", "SYM-QUOTE")
    ]

    # Result sekarang formatnya: ('S', [chunk1, chunk2, ...])
    result = parser.syntactic_parse(tokens)
    
    output_txt_path = r"F:\Vita 1.0\preprocessing\nlp\parser\sintatic\test.txt"

    # PERBAIKAN LOGIKA PENGECEKAN
    if result and isinstance(result, tuple) and len(result) > 1:
        chunks_content = result[1] # Ambil isi dari ('S', chunks)
        
        if isinstance(chunks_content, list):
            ppront.pretty_print_to_file(chunks_content, output_txt_path)
            print(f"[RISA INFO] File berhasil diperbarui di:\n{output_txt_path}")
        else:
            print("[RISA GAGAL] Isi chunk bukan list.")
    else:
        print("[RISA GAGAL] Parsing kosong atau format salah.")


    """
    (",", "SYM-SEP"),

    ("Tapi", "CON-JOINT"),
    (",", "SYM-SEP"),
    ("tentu", "MOD-EMPH"),
    ("saja", "MOD-EMPH"),
    (",", "SYM-SEP"),
    ("mereka", "PRP-PER"),
    ("tidak", "MOD-NEG"),
    ("peduli", "VB-STAT"),
    ("—", "SYM-DASH"),
    ("bahkan", "MOD-EMPH"),
    ("sangat", "MOD-EMPH"),
    ("senang", "JJ-EMOTION"),
    ("!", "SYM-SEP"),
    ("‘", "SYM-QUOTE"),
    ("Kenapa", "Q-REASON"),
    ("?", "SYM-QUOTE"),
    ("‘", "SYM-QUOTE"),
    ("tanyamu", "VB-ACT"),
    ("kemudian", "MOD-TEMP"),
    (",", "SYM-SEP"),
    """

    