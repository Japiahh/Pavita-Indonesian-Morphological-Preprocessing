import re
import math
from collections import defaultdict

from .module.handle_ambiguity import Handleambiguity

from .data import regex_patterns

class ErisaPOSTagger :
    def __init__(self, model=None, mode="", verbose=False):
        self.model = model
        self.mode = mode
        self.verbose = verbose
        self.rules = self.load_rules()
        self.ambiguity_handler = Handleambiguity()

#fungsi pendukung
    def load_rules(self):
        """
        memuat dataset yang diperlukan untuk tagging 
        - lexicon : kamus kata dan tag (27 tag)
        - prob : probabilitas transisi antar tag (27 pola)
        - regex_patterns : pola regex untuk tagging (34 label)
        """
        self.regex_patterns = regex_patterns
        return {
            "regex_patterns": self.regex_patterns
        }
    
#fungsi utama
    def posttag(self, tokens):
        """
        Modul utama tagging (Versi Robust/Anti-Crash).
        """
        # 1. Regex tagging
        regex_tags = {}
        # Tambahkan try-except agar aman
        try:
            regex_results = self.regex_tagging(tokens)
            if regex_results:
                for i, res in enumerate(regex_results):
                    # Validasi format tuple (token, tag)
                    if res and isinstance(res, tuple) and len(res) == 2:
                        _, tag = res
                        if tag is not None:
                            regex_tags[i] = tag
        except Exception:
            pass # Lanjut jika regex error

        # 2. Lexicon tagging
        lexicon_tags = {}
        try:
            for i, token in enumerate(tokens):
                tag = self.lookup_lexicon(token)
                if tag:
                    lexicon_tags[i] = tag
        except Exception:
            pass

        # 3. Gabungkan regex dan lexicon
        combined_tags = {}
        for i in range(len(tokens)):
            if i in lexicon_tags:
                combined_tags[i] = lexicon_tags[i]
            elif i in regex_tags:
                combined_tags[i] = regex_tags[i]

        # 4. Buat pasangan (token, tag) sementara
        token_tag_pairs = [(tokens[i], combined_tags.get(i)) for i in range(len(tokens))]

        # 5. Merge konfiks dan kata ulang
        try:
            token_tag_pairs = self.merge_tokens(token_tag_pairs)
        except Exception:
            # Jika merge gagal, gunakan data lama jangan crash
            pass

        # 6. Infer tagging (FIX UTAMA DI SINI)
        for i, (token, tag) in enumerate(token_tag_pairs):
            if tag is None:
                try:
                    inferred_list = self.infer_tag([token])
                    # CEK DULU: Apakah list ada isinya?
                    if inferred_list and len(inferred_list) > 0:
                        first_item = inferred_list[0]
                        # CEK DULU: Apakah tuple valid?
                        if isinstance(first_item, tuple) and len(first_item) > 1:
                            inferred_tag = first_item[1]
                            if inferred_tag:
                                token_tag_pairs[i] = (token, inferred_tag)
                except Exception:
                    pass # Biarkan None jika infer gagal

        # 7. Rule-based tagging
        try:
            rule_based = self.rule_based_tagging(token_tag_pairs)
            # Pastikan panjangnya sinkron
            if rule_based and len(rule_based) == len(token_tag_pairs):
                for i, (token, tag) in enumerate(rule_based):
                    if tag:
                        token_tag_pairs[i] = (token, tag)
        except Exception:
            pass

        # 8. Viterbi decoding
        merged_tokens = [token for token, _ in token_tag_pairs]
        viterbi_result = []
        try:
            viterbi_result = self.viterbi(merged_tokens)
        except Exception:
            viterbi_result = []

        # 9. Final output (FIX UTAMA KE-2 DI SINI)
        final_tags = []
        for i, (token, tag) in enumerate(token_tag_pairs):
            if tag:
                final_tags.append((token, tag))
            else:
                # Fallback aman
                vt_tag = "NN-COM" # Default paling aman (Benda)
                
                # Cek index sebelum akses array
                if i < len(viterbi_result):
                    res = viterbi_result[i]
                    if res and res != 'UNK':
                        vt_tag = res
                
                final_tags.append((token, vt_tag))

        # 10. Ambiguity handling
        try:
            final_tags = self.posthandle(final_tags)
        except Exception:
            pass

        return final_tags
    
    def posthandle(self, tokens_with_tags):
        """
        Menyatukan token-token morfologis dan mendeteksi batas klausa.
        Cocok dilakukan setelah tagging, kayak kamu yang baru bisa nyimpulin cinta itu palsu setelah disakiti.
        """

        # Step 1: Gabungkan token-token yang layak difusi morfologis
        # (alias mereka yang terlalu rapuh kalau sendirian)
        fused_tokens_with_tags = self.handle_confix_fusion(tokens_with_tags)

        # Step 2: Tangani ambiguitas POS, karena kayak hubungan kamu: banyak makna dan perlu diluruskan~
        disambiguated = self.ambiguity_handler.handle(fused_tokens_with_tags)

        return disambiguated
    
#fungsi tagging
    #deterministik
    def rule_based_tagging(self, tokens):
        """
        Menandai token berdasarkan aturan linguistik manual (misal: prefix, suffix, posisi, dll).
        Digunakan untuk token yang tidak dikenali oleh lexicon dan regex.
        """
        tagged = []

        # Tangani input jika berupa list of str
        if all(isinstance(t, str) for t in tokens):
            tokens = [(t, None) for t in tokens]

        for token, tag in tokens:
            if tag is not None:
                tagged.append((token, tag))
                continue

            # Tangani preposisi "di"
            if token == "di":
                tagged.append((token, "IN"))

            # Prefiks
            elif token.startswith("ber-") or token.startswith("me-") or token.startswith("di-"):
                tagged.append((token, "VB-ACT"))
            elif token.startswith("ter-"):
                tagged.append((token, "VB-STAT"))
            elif token.startswith("se-") and len(token) > 3:
                tagged.append((token, "DT-DEF"))

            # Sufiks
            elif token.endswith("-kan"):
                tagged.append((token, "VB-CAUS"))
            elif token.endswith("-nya"):
                tagged.append((token, "PRP-POSS"))
            elif token.endswith("-an"):
                tagged.append((token, "NN-COM"))

            # Adjektiva
            elif token.endswith("-i") and len(token) > 3:
                tagged.append((token, "VB-STAT"))

            else:
                tagged.append((token, None))

        return tagged
    
    def regex_tagging(self, tokens):
        """
        Menandai token menggunakan pola regex dari dataset regex_patterns.
        Cocok untuk tag deterministik seperti angka, pronomina, dan preposisi umum.
        """
        tagged = []
        for token in tokens:
            tag_assigned = False
            for pattern, tag in self.regex_patterns.items():
                if re.fullmatch(pattern, token):
                    tagged.append((token, tag))  # Pastikan tuple (token, tag)
                    tag_assigned = True
                    break
            if not tag_assigned:
                tagged.append((token, None))  # Pastikan tuple (token, None)
        return tagged

    def infer_tag(self, tokens):
        """
        Menebak tag berdasarkan ciri morfologi (ber-, me-, -an, -nya, dll)
        saat tidak ditemukan dalam lexicon maupun regex.
        """
        inferred = []
        for token in tokens:
            tag = None

            # Inferensi berdasarkan awalan
            if token.startswith("ber-") or token.startswith("me-") or token.startswith("di-"):
                tag = "VB-ACT"
            elif token.startswith("ter-"):
                tag = "VB-STAT"
            elif token.startswith("ke-") and token.endswith("-an"):
                tag = "NN-ABST"  # Contoh: "kebahagiaan", "kehidupan"

            # Inferensi berdasarkan akhiran IND
            elif token.endswith("-kan"):
                tag = "VB-CAUS"
            elif token.endswith("-nya"):
                tag = "PRP-POSS"
            elif token.endswith("-an"):
                tag = "NN-COM"
            elif token.endswith("-lah"):
                tag = "MOD-EMPH"
            elif token.endswith("-i"):
                tag = "VB-STAT"

            # Inferensi kata ulang (reduplikasi)
            elif "-" in token:
                parts = token.split("-")
                if len(parts) == 2 and parts[0] == parts[1]:
                    tag = "NN-COLL"  # kata ulang: "anak-anak"
                else:
                    tag = "NN-COM"  # contoh: "tahu-tempe"

            # Fallback default (bisa dipasrahkan ke ML nanti)
            if tag is None:
                tag = "<UNK>"  # Set default tag sebagai fallback jika tidak terdeteksi

            inferred.append((token, tag))  # Pastikan tuple (token, tag) selalu dikembalikan

        return inferred
    
    #statistik
    def get_possible_tags(self, token):
        """
        Mengambil kemungkinan tag dari lexicon atau regex pattern untuk suatu token.
        Digunakan sebagai kandidat dalam proses probabilistik.
        """
        possible_tags = set()

        # 2. Cek apakah cocok dengan pola regex
        for tag, patterns in self.regex_patterns.items():
            for pattern in patterns:
                if re.fullmatch(pattern, token):
                    possible_tags.add(tag)

        # 3. Jika tidak ditemukan, coba tebak secara morfologis
        if not possible_tags:
            if token.startswith(("me-", "ber-", "di-", "men-", "mem-", "ter-")):
                possible_tags.add("VB-ACT")
            if token.endswith("-an"):
                possible_tags.add("NN-COM")
            if token.endswith(("-nya", "-ku")):
                possible_tags.add("PRP-POSS")
            if "-" in token:
                parts = token.split("-")
                if len(parts) == 2 and parts[0] == parts[1]:
                    possible_tags.add("NN-COLL")

        return list(possible_tags)
    
    def merge_tokens(self, token_tag_pairs):
        merged = []
        i = 0
        while i < len(token_tag_pairs):
            token, tag = token_tag_pairs[i]

            # CASE 1: Langsung "sama-sama"
            if token.lower() == "sama-sama":
                merged.append(("sama-sama", "INT-RESP"))
                i += 1
                continue

            # CASE 2: "sama", "-", "sama" → INT-RESP
            if (i + 2) < len(token_tag_pairs):
                t1, _ = token_tag_pairs[i]
                t2, _ = token_tag_pairs[i + 1]
                t3, _ = token_tag_pairs[i + 2]
                if t1.lower() == "sama" and t2 == "-" and t3.lower() == "sama":
                    merged.append(("sama-sama", "INT-RESP"))
                    i += 3
                    continue
                # CASE 3: token, "-", token (ulang selain "sama") → NN-REPEAT
                elif t2 == "-" and t1 == t3:
                    merged.append((f"{t1}-{t3}", "NN-REPEAT"))
                    i += 3
                    continue

            # CASE 4: "sama", "sama" → INT-RESP
            if (i + 1) < len(token_tag_pairs):
                t1, _ = token_tag_pairs[i]
                t2, _ = token_tag_pairs[i + 1]
                if t1.lower() == "sama" and t2.lower() == "sama":
                    merged.append(("sama-sama", "INT-RESP"))
                    i += 2
                    continue

            # Khusus: kalau token sekarang normal, token berikut "-" (SYM), token sesudahnya berbeda => jangan gabung
            if (i + 2) < len(token_tag_pairs):
                next_token, next_tag = token_tag_pairs[i + 1]
                next2_token, next2_tag = token_tag_pairs[i + 2]
                if next_token == '-' and token != next2_token:
                    merged.append((token, tag))
                    merged.append(('-', 'SYM-DASH'))
                    i += 2
                    continue

            # Default: tambahkan token
            merged.append((token, tag))
            i += 1

        return merged

    def viterbi(self, tokens):
        """
        Menggunakan algoritma Viterbi untuk menentukan urutan tag terbaik berdasarkan
        probabilitas transisi dan kemungkinan tag (lexicon/regex). SUB
        """
        V = [{}]  # Probabilitas maksimal pada setiap step
        path = {}  # Menyimpan path tag terbaik

        # Step 0: Inisialisasi dengan token pertama
        first_token = tokens[0]
        first_tags = self.get_possible_tags(first_token)
        for tag in first_tags:
            V[0][tag] = self.score("<s>", tag)  # Probabilitas transisi dari start token
            path[tag] = [tag]

        # Step 1-n: Iterasi untuk token selanjutnya
        for t in range(1, len(tokens)):
            V.append({})
            new_path = {}
            curr_token = tokens[t]
            possible_tags = self.get_possible_tags(curr_token)

            for curr_tag in possible_tags:
                best_score = float('-inf')
                best_prev_tag = None

                for prev_tag in V[t - 1]:
                    score = V[t - 1][prev_tag] + self.score(prev_tag, curr_tag)

                    if score > best_score:
                        best_score = score 
                        best_prev_tag = prev_tag

                if best_prev_tag is not None:
                    V[t][curr_tag] = best_score
                    new_path[curr_tag] = path[best_prev_tag] + [curr_tag]

            path = new_path

        # Step akhir: Ambil tag sequence terbaik
        if not V[-1]:
            return ["<UNK>"] * len(tokens)  # Jika gagal total, fallback

        max_final_tag = max(V[-1], key=lambda tag: V[-1][tag])
        return path[max_final_tag]

#fungsi Handle
    def handle_confix_fusion(self, tokens_with_tags):
        """
        Menggabungkan token morfem (prefix-, -suffix) menjadi kata utuh
        BERDASARKAN keberadaan tanda strip (-).
        """
        fused = []
        i = 0
        n = len(tokens_with_tags)

        # Daftar Prefix & Suffix Valid (untuk validasi tambahan)
        valid_prefixes = {"di", "me", "ber", "ter", "mem", "men", "meng", "ke", "pe", "se", "pen", "pem", "per"}
        valid_suffixes = {"i", "kan", "an", "nya", "lah", "kah", "ku", "mu", "pun"}
        
        # Mapping Suffix Ganda
        double_suffix_map = {
            ("an", "nya"): "NN-COM",
            ("kan", "nya"): "VB-ACT",
            ("i", "lah"): "VB-ACT",
            ("kan", "lah"): "VB-ACT",
            ("an", "ku"): "NN-COM",
            ("an", "mu"): "NN-COM",
        }

        while i < n:
            # Ambil token saat ini untuk pengecekan awal
            curr_tok, curr_tag = tokens_with_tags[i]

            # ---------------------------------------------------------
            # 1. CEK 4 TOKEN: Prefix- + Root + -Suffix + -Suffix
            # Syarat: Token pertama harus berakhiran '-', Token 3 & 4 berawalan '-'
            # ---------------------------------------------------------
            if i + 3 < n:
                p_tok, p_tag = tokens_with_tags[i]
                r_tok, r_tag = tokens_with_tags[i+1]
                s1_tok, s1_tag = tokens_with_tags[i+2]
                s2_tok, s2_tag = tokens_with_tags[i+3]

                # STRICT CHECK: Pastikan ada strip
                if (p_tok.endswith('-') and s1_tok.startswith('-') and s2_tok.startswith('-')):
                    c_pref = p_tok.strip('-')
                    c_suf1 = s1_tok.strip('-')
                    c_suf2 = s2_tok.strip('-')

                    if c_pref in valid_prefixes:
                        new_token = c_pref + r_tok + c_suf1 + c_suf2
                        
                        # Logika Tagging (Sama seperti kodemu)
                        new_tag = "VB-ACT" # Default
                        if c_pref == "di": new_tag = "VB-PASS"
                        elif c_pref in ["ber", "ter"]: new_tag = "VB-STAT"
                        elif c_pref in ["pe", "pen", "pem", "per"]: new_tag = "NN-COM"
                        
                        fused.append((new_token, new_tag))
                        i += 4
                        continue

            # ---------------------------------------------------------
            # 2. CEK 3 TOKEN: Prefix- + Root + -Suffix
            # Syarat: Token pertama berakhiran '-', Token ketiga berawalan '-'
            # ---------------------------------------------------------
            if i + 2 < n:
                p_tok, p_tag = tokens_with_tags[i]
                r_tok, r_tag = tokens_with_tags[i+1]
                s_tok, s_tag = tokens_with_tags[i+2]

                if (p_tok.endswith('-') and s_tok.startswith('-')):
                    c_pref = p_tok.strip('-')
                    c_suf = s_tok.strip('-')
                    
                    if c_pref in valid_prefixes:
                        new_token = c_pref + r_tok + c_suf
                        
                        # Logika Tagging
                        new_tag = "VB-ACT"
                        if c_pref == "di": new_tag = "VB-PASS"
                        elif c_pref in ["ber", "ter"]: new_tag = "VB-STAT"
                        elif c_pref == "ke" and c_suf == "an": new_tag = "NN-ABST"
                        elif c_pref in ["pe", "pen", "pem", "per"]: new_tag = "NN-COM"
                        elif c_pref == "se":
                            if c_suf == "nya": new_tag = "ADV-ATT" # secepatnya
                            else: new_tag = "NN-COM"

                        fused.append((new_token, new_tag))
                        i += 3
                        continue

            # ---------------------------------------------------------
            # 3. CEK 3 TOKEN: Root + -Suffix + -Suffix (Tanpa Prefix)
            # Syarat: Token 2 & 3 berawalan '-'
            # ---------------------------------------------------------
            if i + 2 < n:
                r_tok, r_tag = tokens_with_tags[i]
                s1_tok, s1_tag = tokens_with_tags[i+1]
                s2_tok, s2_tag = tokens_with_tags[i+2]

                if (s1_tok.startswith('-') and s2_tok.startswith('-')):
                    c_suf1 = s1_tok.strip('-')
                    c_suf2 = s2_tok.strip('-')

                    if (c_suf1, c_suf2) in double_suffix_map:
                        new_token = r_tok + c_suf1 + c_suf2
                        new_tag = double_suffix_map[(c_suf1, c_suf2)]
                        fused.append((new_token, new_tag))
                        i += 3
                        continue

            # ---------------------------------------------------------
            # 4. CEK 2 TOKEN: Prefix- + Root
            # Syarat: Token pertama HARUS berakhiran '-'
            # ---------------------------------------------------------
            if i + 1 < n:
                p_tok, p_tag = tokens_with_tags[i]
                r_tok, r_tag = tokens_with_tags[i+1]

                # INI KUNCI PERBAIKAN UNTUK KASUS 'di' vs 'se-'
                if p_tok.endswith('-'): 
                    c_pref = p_tok.strip('-')
                    
                    if c_pref in valid_prefixes:
                        # Cek Root valid (bukan simbol)
                        if not r_tag.startswith("SYM"):
                            new_token = c_pref + r_tok
                            
                            # Logika Tagging
                            new_tag = "VB-ACT"
                            if c_pref == "di": new_tag = "VB-PASS"
                            elif c_pref in ["ber", "ter"]: new_tag = "VB-STAT"
                            elif c_pref in ["pe", "pen", "pem", "per"]: new_tag = "NN-COM"
                            elif c_pref == "se":
                                # se-buah -> DT-NUM (Satu)
                                # se-orang -> DT-NUM
                                if r_tok in ["buah", "orang", "ekor", "kali"]: 
                                    new_tag = "DT-NUM"
                                else:
                                    new_tag = "ADV-ATT" # se-lama, se-cepat

                            elif c_pref == "ke":
                                if r_tag == "DT-NUM": new_tag = "DT-ORD" # ke-dua
                                else: new_tag = "NN-COM"

                            fused.append((new_token, new_tag))
                            i += 2
                            continue

            # ---------------------------------------------------------
            # 5. CEK 2 TOKEN: Root + -Suffix
            # Syarat: Token kedua HARUS berawalan '-'
            # ---------------------------------------------------------
            if i + 1 < n:
                r_tok, r_tag = tokens_with_tags[i]
                s_tok, s_tag = tokens_with_tags[i+1]

                if s_tok.startswith('-'):
                    c_suf = s_tok.strip('-')
                    if c_suf in valid_suffixes:
                        new_token = r_tok + c_suf
                        
                        # Logika Tagging Suffix
                        new_tag = r_tag # Default ikut root
                        if c_suf == "an": new_tag = "NN-COM"
                        elif c_suf == "nya": 
                            # Cek root tag
                            if r_tag.startswith("VB"): new_tag = "NN-COM" # turunan
                            else: new_tag = "NN-COM" # bukunya (POSS di merge jadi NN-COM biasanya)
                        elif c_suf in ["kan", "i"]: new_tag = "VB-ACT"
                        elif c_suf in ["ku", "mu"]: new_tag = "NN-COM"
                        
                        fused.append((new_token, new_tag))
                        i += 2
                        continue

            # ---------------------------------------------------------
            # 6. Default: Token Tidak Berubah (Simpan apa adanya)
            # ---------------------------------------------------------
            fused.append(tokens_with_tags[i])
            i += 1

        return fused

if __name__ == "__main__":
    tagger = ErisaPOSTagger(verbose=True)
    tagged = tagger.posttag([
        'dia', 'duduk', 'di', 'se-', 'buah', 'kelapa', ',', 'lalu', 'me-', 'makan', '-nya', 'sambil', 'ter-', 'senyum', 'lembut', '.', 'meski', '-pun', 'warna', 'kelapa', 'itu', 'aneh', '.', 'kau', 'tahu', 'jawab', '-an', '-nya', 'sejak', 'tadi', ',', 'kan', '?'
    ])  

    sentences = []
    current = []

    for token, tag in tagged:
        current.append((token, tag))
        if token == ".":
            sentences.append(current)
            current = []

    print("Hasil tagging:\n")
    for sentence in sentences:
        print(sentence)
        print()