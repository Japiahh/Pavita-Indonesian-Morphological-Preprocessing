class FindDepedency:
    def __init__(self):
        pass

    def _normalize_input(self, syntactic_data):
        if isinstance(syntactic_data, tuple) and len(syntactic_data) > 1:
            if isinstance(syntactic_data[1], list):
                return syntactic_data[1]
        
        if isinstance(syntactic_data, list):
            return syntactic_data
            
        return []

    def find_root(self, syntactic_data):
        data = self._normalize_input(syntactic_data)

        for node in data:
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'VP':
                    for item in content:
                        if isinstance(item, tuple) and len(item) == 2:
                            word, tag = item
                            if isinstance(tag, str) and tag.startswith("VB"):
                                return item 

            elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                word, tag = node
                if tag.startswith("VB"):
                    return node

        return None

    def find_nsubj(self, syntactic_data):
        data = self._normalize_input(syntactic_data)

        for node in data:
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'NP':
                    for item in content:
                        if isinstance(item, tuple) and len(item) == 2:
                            word, tag = item
                            if isinstance(tag, str) and (tag.startswith("PRP") or tag.startswith("NN")):
                                return item

            elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                word, tag = node
                if tag.startswith("PRP") or tag.startswith("NN"):
                    return node

        return None

    def find_dobj(self, syntactic_data):
        data = self._normalize_input(syntactic_data)

        for node in data:
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                label, content = node
                if label == 'VP': 
                    for subnode in content:
                        if isinstance(subnode, tuple) and len(subnode) == 2 and isinstance(subnode[1], list):
                            sub_label, sub_content = subnode
                            if sub_label == 'NP':
                                for item in sub_content:
                                    if isinstance(item, tuple) and len(item) == 2:
                                        w, t = item
                                        if isinstance(t, str) and (t.startswith("NN") or t.startswith("PRP")):
                                            return item
                        
                        elif isinstance(subnode, tuple) and len(subnode) == 2 and isinstance(subnode[1], str):
                             w, t = subnode
                             if t.startswith("NN") or t.startswith("PRP"):
                                 return subnode
        return None

    def find_obj(self, syntactic_data):
        return self.find_dobj(syntactic_data)

    def find_xcomp(self, syntactic_data):
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

                    if label in ['VP', 'SBAR'] and isinstance(content, list):
                         pass

                    if isinstance(content, list):
                        recursive_search(content)

        recursive_search(data)
        return xcomp_clauses

    def find_punctuation(self, syntactic_data):
        data = self._normalize_input(syntactic_data)
        punctuations = []

        def recursive_search(nodes):
            for node in nodes:
                if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], list):
                    label, content = node
                    if label == 'PUNCT':
                        for item in content:
                             if isinstance(item, tuple): punctuations.append(item)
                    else:
                        recursive_search(content)

                elif isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], str):
                    w, t = node
                    if t.startswith("SYM") or t == 'PUNCT':
                        punctuations.append(node)

        recursive_search(data)

        return punctuations
