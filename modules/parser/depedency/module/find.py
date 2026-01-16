class FindDepedency:
    def __init__(self):
        pass

    def _normalize_input(self, syntactic_data):
        """
        Helper internal untuk memastikan kita memproses LIST of chunks,
        bukan Tuple Root ('S', list).
        """
        # Jika input berupa Tuple ('S', [...]), ambil list isinya
        if isinstance(syntactic_data, tuple) and len(syntactic_data) > 1:
            if isinstance(syntactic_data[1], list):
                return syntactic_data[1]
        
        # Jika sudah berupa list, kembalikan langsung
        if isinstance(syntactic_data, list):
            return syntactic_data
            
        # Jika tidak dikenali, kembalikan list kosong agar tidak crash iteration
        return []

    def find_root(self, syntactic_data):
        """
        Mencari kata kerja utama (root).
        Mampu menangani Verb di dalam VP chunk maupun Verb yang berdiri sendiri (flat structure).
        """
        data = self._normalize_input(syntactic_data)

        for node in data:
            # Kasus 1: Node adalah Chunk ('VP', [...])
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'VP':
                    # Cek isi VP untuk cari Verb
                    for item in content:
                        if isinstance(item, tuple) and len(item) == 2:
                            word, tag = item
                            if isinstance(tag, str) and tag.startswith("VB"):
                                return item 

            # Kasus 2: Node adalah Token langsung ('Makan', 'VB-ACT') - Fallback structure
            elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                word, tag = node
                if tag.startswith("VB"):
                    return node

        return None

    def find_nsubj(self, syntactic_data):
        """
        Mencari noun phrase (subjek kalimat).
        """
        data = self._normalize_input(syntactic_data)

        for node in data:
            # Kasus 1: Chunk ('NP', [...])
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'NP':
                    # Ambil head noun dari NP
                    for item in content:
                        if isinstance(item, tuple) and len(item) == 2:
                            word, tag = item
                            if isinstance(tag, str) and (tag.startswith("PRP") or tag.startswith("NN")):
                                return item

            # Kasus 2: Token langsung ('Saya', 'PRP')
            elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                word, tag = node
                if tag.startswith("PRP") or tag.startswith("NN"):
                    return node

        return None

    def find_dobj(self, syntactic_data):
        """
        Mencari direct object (Objek Penderita) -> Biasanya di dalam VP.
        """
        data = self._normalize_input(syntactic_data)

        for node in data:
            # Kita cari VP dulu, karena objek biasanya anak dari VP
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'VP': 
                    for subnode in content:
                        # Pola 1: Ada Chunk NP di dalam VP
                        if isinstance(subnode, tuple) and len(subnode) == 2 and isinstance(subnode[1], list):
                            sub_label, sub_content = subnode
                            if sub_label == 'NP':
                                for item in sub_content:
                                    if isinstance(item, tuple) and len(item) == 2:
                                        w, t = item
                                        if isinstance(t, str) and (t.startswith("NN") or t.startswith("PRP")):
                                            return item
                        
                        # Pola 2: Token langsung di dalam VP (misal: makan [nasi])
                        elif isinstance(subnode, tuple) and len(subnode) == 2 and isinstance(subnode[1], str):
                             w, t = subnode
                             if t.startswith("NN") or t.startswith("PRP"):
                                 return subnode
        return None

    def find_obj(self, syntactic_data):
        """ Alias untuk find_dobj """
        return self.find_dobj(syntactic_data)

    def find_xcomp(self, syntactic_data):
        """
        Mencari Open Clausal Complement (Recursive Search).
        """
        # Tidak perlu normalize di sini karena recursive_search akan handle traversing
        data = syntactic_data 
        if isinstance(syntactic_data, tuple) and syntactic_data[0] == 'S':
             data = syntactic_data[1]

        xcomp_clauses = []

        def recursive_search(nodes):
            if not isinstance(nodes, list): return

            for node in nodes:
                if isinstance(node, tuple) and len(node) == 2:
                    label = node[0]
                    content = node[1]
                    
                    # Jika ketemu VP, cek apakah ini kandidat xcomp
                    # (Logic sederhana: VP di dalam list yang bukan top-level nsubj)
                    if label in ['VP', 'SBAR'] and isinstance(content, list):
                         # Di sini bisa ditambahkan logika lebih kompleks
                         pass

                    # Recursion ke anak-anaknya
                    if isinstance(content, list):
                        recursive_search(content)

        recursive_search(data)
        return xcomp_clauses

    def find_punctuation(self, syntactic_data):
        """
        Mengembalikan daftar semua tanda baca.
        """
        # Gunakan normalize agar start point benar
        data = self._normalize_input(syntactic_data)
        punctuations = []

        def recursive_search(nodes):
            for node in nodes:
                # Cek Chunk
                if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                    label, content = node
                    if label == 'PUNCT':
                        # Ambil semua isinya
                        for item in content:
                             if isinstance(item, tuple): punctuations.append(item)
                    else:
                        # Recurse
                        recursive_search(content)
                
                # Cek Token Langsung
                elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                    w, t = node
                    if t.startswith("SYM") or t == 'PUNCT':
                        punctuations.append(node)

        recursive_search(data)
        return punctuations