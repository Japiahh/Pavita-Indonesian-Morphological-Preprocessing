
class Chunking:
    def __init__(self):
        pass

    def is_np_token(self, tag):
        return tag.split("-")[0] in {"DT", "PRP", "NN"} 

    def is_adj_token(self, tag):
        return tag in {"JJ-EMOTION", "JJ-QUALITY", "MOD"}

    def is_adv_token(self, tag):
        return tag.split("-")[0] in {"MOD", "ADV"}
    
    def is_adjp_token(self, tag):
        return tag in {"JJ-EMOTION", "JJ-QUALITY", "MOD"}

    def is_advp_token(self, tag):
        return tag.split("-")[0] in {"MOD", "ADV"}

    def is_wh_token(self, tag):
        return tag.startswith("WH") or tag.startswith("PRP-INT")

    def build_np(self, tokens, i):
        np_buffer = []
        start_i = i

        while i < len(tokens):
            tag = tokens[i][1]

            # Token valid untuk NP
            if self.is_np_token(tag):
                np_buffer.append(tokens[i])
                i += 1

            # Terima JJ modifier non-predikatif
            elif tag.startswith("JJ") and tag != "JJ-QUALITY":
                np_buffer.append(tokens[i])
                i += 1

            else:
                break  # stop kalau ketemu JJ-QUALITY atau tag aneh lain

        # Cek apakah token berikutnya JJ-QUALITY atau VB predikatif
        if i < len(tokens):
            next_tag = tokens[i][1]
            if next_tag == "JJ-QUALITY" or next_tag.startswith("VB"):
                vp_chunk, i = self.build_vp(tokens, i)
                return [('NP', np_buffer), vp_chunk], i

        return ('NP', np_buffer), i

    def build_adjp(self, tokens, i):
        adjp_buffer = [tokens[i]]
        i += 1
        while i < len(tokens) and self.is_adj_token(tokens[i][1]):
            adjp_buffer.append(tokens[i])
            i += 1
        return ('ADJP', adjp_buffer), i

    def build_advp(self,tokens, i):
        advp_buffer = [tokens[i]]
        i += 1
        while i < len(tokens) and self.is_adv_token(tokens[i][1]):
            advp_buffer.append(tokens[i])
            i += 1
        return ('ADVP', advp_buffer), i

    def build_vp(self, tokens, i):
        vp_buffer = []

        # [0] Tangani VB awal sebelum MOD
        if i < len(tokens) and tokens[i][1].startswith("VB"):
            vp_buffer.append(tokens[i])
            i += 1

        # [1] Tangani pembuka: MOD-TEMP, MOD-ACT (misalnya "sambil")
        if i < len(tokens) and tokens[i][1] in {"MOD-TEMP", "MOD-ACT"}:
            mod_token = tokens[i]
            i += 1
            if i < len(tokens) and tokens[i][1].startswith("VB"):
                nested_vp, i = self.build_vp(tokens, i)
                vp_buffer.append(('PP', [mod_token, nested_vp]))  # lanjutkan VP, jangan kabur dulu kayak komitmen kamu
            else:
                vp_buffer.append(mod_token)

        # [2] Tangani pembuka PP: preposisi (IN-*)
        elif i < len(tokens) and tokens[i][1].startswith("IN-"):
            in_token = tokens[i]
            i += 1

            # Kalau setelah IN ada VB → nested VP
            if i < len(tokens) and tokens[i][1].startswith("VB"):
                nested_vp, i = self.build_vp(tokens, i)
                return ('VP', [('PP', [in_token, nested_vp])]), i

            # Kalau bukan VB, bisa NP atau ADVP
            np_buffer = []
            while i < len(tokens) and self.is_np_token(tokens[i][1]):
                np_buffer.append(tokens[i])
                i += 1

            advp_buffer = []
            while i < len(tokens) and self.is_adv_token(tokens[i][1]):
                advp_buffer.append(tokens[i])
                i += 1

            if np_buffer:
                vp_buffer.append(('PP', [in_token, ('NP', np_buffer)]))
            elif advp_buffer:
                vp_buffer.append(('PP', [in_token, ('ADVP', advp_buffer)]))
            else:
                vp_buffer.append(('PP', [in_token]))

        # [3] Masukkan PP yang sudah dalam bentuk chunk
        while i < len(tokens) and isinstance(tokens[i], tuple) and tokens[i][0] == 'PP':
            vp_buffer.append(tokens[i])
            i += 1

        # [4] Tangani kata kerja utama
        if i < len(tokens) and tokens[i][1].startswith("VB"):
            # Hindari duplikasi jika sebelumnya udah nested VP
            if not (vp_buffer and isinstance(vp_buffer[-1], tuple) and vp_buffer[-1][0] in {"PP", "VP"}):
                vp_buffer.append(tokens[i])
                i += 1

        # [5] Tangani objek (NP) setelah VB
        if i < len(tokens) and self.is_np_token(tokens[i][1]):
            np_chunk, new_i = self.build_np(tokens, i)
            if np_chunk:
                vp_buffer.append(np_chunk)
                i = new_i

        # [6] Tangani modifier tambahan: ADV atau JJ-QUALITY
        while i < len(tokens) and (
            tokens[i][1].startswith("ADV") or tokens[i][1] == "JJ-QUALITY"
        ):
            vp_buffer.append(tokens[i])
            i += 1

        # [7] Tangani trailing PP pelengkap lanjutan (VP → PP)
        while i < len(tokens) and tokens[i][1].startswith("IN-"):
            in_token = tokens[i]
            i += 1

            np_buffer = []
            while i < len(tokens) and self.is_np_token(tokens[i][1]):
                np_buffer.append(tokens[i])
                i += 1

            advp_buffer = []
            while i < len(tokens) and self.is_adv_token(tokens[i][1]):
                advp_buffer.append(tokens[i])
                i += 1

            if i < len(tokens) and tokens[i][1].startswith("VB"):
                nested_vp, i = self.build_vp(tokens, i)
                vp_buffer.append(('PP', [in_token, nested_vp]))
            elif np_buffer:
                vp_buffer.append(('PP', [in_token, ('NP', np_buffer)]))
            elif advp_buffer:
                vp_buffer.append(('PP', [in_token, ('ADVP', advp_buffer)]))
            else:
                vp_buffer.append(('PP', [in_token]))

        # [8] Masukkan lagi PP chunk yang mungkin muncul belakangan
        while i < len(tokens) and isinstance(tokens[i], tuple) and tokens[i][0] == 'PP':
            vp_buffer.append(tokens[i])
            i += 1

        return ('VP', vp_buffer), i

    def build_pp(self, tokens, i):
        in_token = tokens[i]
        i += 1

        # [1] Kalau setelah IN ada ADVP (misal: "dengan cepat")
        if i < len(tokens) and self.is_adv_token(tokens[i][1]):
            advp_buffer = []
            while i < len(tokens) and self.is_adv_token(tokens[i][1]):
                advp_buffer.append(tokens[i])
                i += 1
            return ('PP', [in_token, ('ADVP', advp_buffer)]), i

        # [2] Kalau setelah IN ada chunk NP, langsung pakai aja
        if i < len(tokens) and isinstance(tokens[i], tuple) and tokens[i][0] == 'NP':
            return ('PP', [in_token, tokens[i]]), i + 1

        # [3] Kalau setelah IN ada NP biasa (token), baru kita kumpulin manual
        np_buffer = []
        while i < len(tokens) and self.is_np_token(tokens[i][1]):
            np_buffer.append(tokens[i])
            i += 1
        if np_buffer:
            return ('PP', [in_token, ('NP', np_buffer)]), i

        # [4] Kalau gak ada apa-apa, ya udah... nasib. IN doang.
        return ('PP', [in_token]), i

    def build_interrog(self, tokens, i):
        # WH types sesuai label barumu
        if not tokens[i][1].startswith("Q-"):
            return None

        wh_buffer = [tokens[i]]
        i += 1

        # Tangkap kutipan setelah WH, misalnya: "apa 'itu'?"
        while i < len(tokens) and tokens[i][1].startswith("SYM-QUOTE"):
            wh_buffer.append(tokens[i])
            i += 1

        interrog_buffer = [('WH', wh_buffer)]
        vp_buffer = []

        # Token yang valid untuk bagian VP dari pertanyaan
        while i < len(tokens) and not tokens[i][1].startswith("SYM"):
            tag_root = tokens[i][1].split("-")[0]
            if tag_root in {"VB", "MOD", "ADV", "NN", "PRP", "IN", "DT", "JJ"}:
                vp_buffer.append(tokens[i])
                i += 1
            else:
                break

        if vp_buffer:
            interrog_buffer.append(('VP', vp_buffer))

        return ('INTERROG', interrog_buffer), i

