import re

# Pastikan import ini sesuai
from .module.find import FindDepedency

class ZhyaniDependencyParser:
    def __init__ (self):
        """
        Inisialisasi parser.
        """
        self.finder = FindDepedency()

#fungsi utama
    def dependency_parse(self, syntactic_tree):
        """
        Fungsi Utama (Main Interface).
        1. Menerima input (Pohon/Tokens).
        2. Memecahnya menjadi kalimat-kalimat.
        3. Menganalisis dependensi tiap kalimat.
        """
        # 1. Normalisasi Input (Tuple vs List)
        data_to_process = syntactic_tree
        if isinstance(syntactic_tree, tuple) and len(syntactic_tree) > 1:
            data_to_process = syntactic_tree[1] # Ambil isi listnya

        if not data_to_process:
            return []

        # 2. Pecah menjadi beberapa kalimat
        sentences_list = self.sentence_split(data_to_process)
        
        final_results = []

        # 3. Loop setiap kalimat dan cari dependensinya
        for idx, sentence in enumerate(sentences_list):
            if not sentence: continue
            
            # Analisis kalimat ini
            dep_data = self.all_find(sentence)
            
            # Bungkus hasilnya
            # Text reconstruction harus handle Chunk vs Token
            text_parts = []
            for t in sentence:
                if isinstance(t, tuple):
                    if isinstance(t[1], list): # Chunk ('NP', [tokens])
                        text_parts.extend([sub[0] for sub in t[1] if isinstance(sub, tuple)])
                    else: # Token ('Kata', 'Tag')
                        text_parts.append(t[0])

            sentence_output = {
                "sentence_id": idx + 1,
                "text": " ".join(text_parts),
                "dependencies": dep_data
            }
            final_results.append(sentence_output)

        return final_results

#fungsi
    def sentence_split(self, tokens):
        """
        Memecah kalimat menjadi beberapa bagian berdasarkan tanda baca akhir kalimat 
        dan titik dua kontekstual (Versi Safe/Anti-Crash).
        
        :param tokens: List of tuples
        :return: List of list of tuples
        """
        if not tokens:
            return []
        
        # Normalisasi input jadi list
        if not isinstance(tokens, list):
            if isinstance(tokens, tuple):
                tokens = list(tokens)
            else:
                return [] 

        sentence_endings = {'.', '?', '!'}
        valid_after_colon = {'PRP-PER', 'PRP-DEM', 'VB-ACT', 'VB-STAT', 'DT-DEF', 'DT-ORD'}
        
        sentences = []
        current_sentence = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            current_sentence.append(token)
            
            # --- DETEKSI ISI TOKEN (Apakah Token Biasa atau Chunk?) ---
            check_word = None
            check_tag = None
            
            # Kasus 1: Token Biasa ('Halo', 'NN')
            if isinstance(token, tuple) and len(token) == 2 and isinstance(token[1], str):
                check_word = token[0]
                check_tag = token[1]

            # Kasus 2: Chunk ('PUNCT', [('.', 'SYM')])
            elif isinstance(token, tuple) and len(token) == 2 and isinstance(token[1], list):
                label = token[0]
                children = token[1]
                # Kita hanya peduli isi chunk jika dia PUNCT atau memiliki tanda baca
                if children and len(children) > 0:
                    first_child = children[0]
                    if isinstance(first_child, tuple) and len(first_child) >= 2:
                        check_word = first_child[0]
                        check_tag = first_child[1]

            # --- LOGIKA PEMISAHAN ---
            if check_word and check_tag:
                tag_str = str(check_tag)

                # Kondisi A: Akhir kalimat biasa
                if check_word in sentence_endings and tag_str.startswith("SYM"):
                    sentences.append(current_sentence)
                    current_sentence = []

                # Kondisi B: Titik dua
                elif check_word == ':' and tag_str.startswith("SYM"):
                    # Lookahead logic (sederhana)
                    # Karena struktur chunk, lookahead jadi kompleks, kita skip dulu untuk kestabilan
                    # atau anggap pemisah jika di akhir blok.
                    pass

            i += 1

        if current_sentence:
            sentences.append(current_sentence)

        return sentences
    
    def all_find(self, syntactic_tree):
        """
        Mengumpulkan semua komponen dependensi (Root, Subjek, Objek, dll)
        dengan memanggil helper class FindDepedency.
        
        Argumen:
            syntactic_tree (list/tuple): Struktur pohon hasil ZhyaniSyntacticParser.
            
        Return:
            dict: Dictionary berisi komponen-komponen dependensi yang ditemukan.
        """
        # Gunakan self.finder yang sudah di-init di __init__
        finder = self.finder 
        
        dependency_components = {
            "root": None,
            "nsubj": None,
            "dobj": None,
            "xcomp": [],
            "punct": []
        }

        if hasattr(finder, 'find_root'):
            dependency_components["root"] = finder.find_root(syntactic_tree)

        if hasattr(finder, 'find_nsubj'):
            dependency_components["nsubj"] = finder.find_nsubj(syntactic_tree)

        if hasattr(finder, 'find_dobj'):
            dependency_components["dobj"] = finder.find_dobj(syntactic_tree)
        # Fallback nama fungsi (obj vs dobj)
        elif hasattr(finder, 'find_obj'):
            dependency_components["dobj"] = finder.find_obj(syntactic_tree)

        if hasattr(finder, 'find_xcomp'):
            dependency_components["xcomp"] = finder.find_xcomp(syntactic_tree)

        if hasattr(finder, 'find_punctuation'):
            dependency_components["punct"] = finder.find_punctuation(syntactic_tree)

        return dependency_components