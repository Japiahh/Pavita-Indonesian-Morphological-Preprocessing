import re
from typing import List
import string

prefixes = [
    "meng", "mem", "men", "me",
    "ber", "ter",
    "se", "per",
    "pe", "pen",
    "di", "ke",
    "ng", 
]
suffixes = ["kan", "nya", "ku", "mu", "an", "i", "in"]
particles = ["lah", "kah", "tah", "pun"]

def load_base_words():
    from .data import kada
    return set(kada["kata_dasar"])

kata_dasar = load_base_words()

class ChakariaTokenizer:
    def __init__(
        self,
        enable_split_affixes=True,
        enable_handle_repeats=True,
        enable_split_particles=True,
        enable_handle_confixes=True,
        use_base_words=True,
        verbose=False,
    ):
        self.enable_split_affixes = enable_split_affixes
        self.enable_handle_repeats = enable_handle_repeats
        self.enable_split_particles = enable_split_particles
        self.enable_handle_confixes = enable_handle_confixes
        self.use_base_words = use_base_words
        self.verbose = verbose


#fungsi utama
    def tokenize(self, text):
        tokens = text.split()

        final_tokens = []
        for token in tokens:
            token_lc = token.lower()
            
            preprocessed = self.pre_handle_split([token_lc])
            final_tokens.extend(preprocessed)

        final_tokens = [t for t in final_tokens if t.strip() != ""]

        return final_tokens


    def pre_handle_split(self, tokens):
        tokens = self.handle_punctuation(tokens)
        if self.enable_handle_repeats:
            new_tokens = []
            for token in tokens:
                if token.lower() in kata_dasar and "-" not in token:
                     new_tokens.append(token)
                else:
                     new_tokens.extend(self.handle_repeats([token]))
            tokens = new_tokens

        if self.enable_split_particles:
            tokens = self.split_particles(tokens)

        if self.enable_split_affixes:
            new_tokens = []
            for token in tokens:
                token_lc = token.lower()

                if token_lc in kata_dasar or token.startswith('-'):
                    new_tokens.append(token)
                    continue

                splitted = self.split_affixes([token])
                
                if len(splitted) > 1 and splitted[0] == 'ku-':
                    stem_part = splitted[1] 
                    
                    if len(stem_part) <= 4:
                        new_tokens.append(token) 
                        continue
                
                new_tokens.extend(splitted)
            
            tokens = new_tokens

        tokens = self._greedy_kada_split(tokens)

        return tokens

#Mechaism
    def _all_final(self, tokens):
        return all(self._is_morphologically_final(t) for t in tokens)

    def _is_morphologically_final(self, token):
        if token not in kata_dasar:
            return False

        for p in prefixes:
            if token.startswith(p):
                return False

        for s in suffixes:
            if token.endswith(s):
                return False

        return True

    def _greedy_kada_split(self, tokens):
        result = []
        i = 0

        while i < len(tokens):
            found_base = None
            found_end = i + 1

            for j in range(i + 1, len(tokens) + 1):
                gabung = ''.join(tokens[i:j])
                if gabung in kata_dasar:
                    found_base = gabung
                    found_end = j

            if found_base:
                result.append(found_base)
                i = found_end
            else:
                result.append(tokens[i])
                i += 1

        return result
    
    def _recursive_split(self, token):
        if "-" in token:
            return [token]

        prefix_processed = self.split_prefix(token)
        
        if len(prefix_processed) > 1 or prefix_processed[0] != token:
            return prefix_processed
            
        suffix_processed = self.split_suffix(token)
        
        return suffix_processed
    
    def _check_deep_validity(self, word):
        if len(word) < 2: 
            return False
            
        if word in kata_dasar:
            return True
            
        suffix_check = self.split_suffix(word)
        if len(suffix_check) > 1: 
            base = suffix_check[0]
            if base in kata_dasar:
                return True
            
            if self._check_deep_validity(base):
                return True

        for prefix in prefixes:
            if word.startswith(prefix):
                stem = word[len(prefix):]
                if len(stem) < len(word):
                    if self._check_deep_validity(stem):
                        return True

        return False
    
    def _get_deep_root(self, word):
        if len(word) < 2: return None
        if word in kata_dasar: return word
            
        suffix_check = self.split_suffix(word)
        if len(suffix_check) > 1:
            base = suffix_check[0]
            if base in kata_dasar: return base
            
            res = self._get_deep_root(base)
            if res: return res

        for prefix in prefixes:
            if word.startswith(prefix):
                stem = word[len(prefix):]
                if len(stem) < len(word): 
                    res = self._get_deep_root(stem)
                    if res: return res
        
        return None
    
#spliting
    def handle_punctuation(self, tokens):
        processed = []
        for token in tokens:
            split = re.findall(r"\w+|[.,!?;:\-\"'\(\)]", token)
            processed.extend(split)
        return processed

    def handle_repeats(self, tokens: List[str]) -> List[str]:
        result = []

        for token in tokens:
            if '-' in token:
                parts = token.split('-')
                if len(parts) == 2 and parts[0] == parts[1]:
                    result.extend([parts[0], '-', parts[1]])
                    continue
                else:
                    result.append(token)
                    continue

            found = False
            for prefix in prefixes:
                if token.startswith(prefix):
                    sisa = token[len(prefix):]
                    if len(sisa) % 2 == 0:
                        half = len(sisa) // 2
                        first = sisa[:half]
                        second = sisa[half:]
                        if first == second and first in kata_dasar:
                            result.extend([prefix, first, second])
                            found = True
                            break

            if found:
                continue

            if len(token) % 2 == 0:
                half = len(token) // 2
                part1 = token[:half]
                part2 = token[half:]
                if part1 == part2 and part1 in kata_dasar:
                    result.extend([part1, part2])
                    continue

            result.append(token)

        return result

    def split_affixes(self, tokens):
        final_result = []

        for token in tokens:
            prefix_processed = self.split_prefix(token)
            stem_candidate = prefix_processed[-1]
            prefixes = prefix_processed[:-1]
            suffix_processed = self.split_suffix(stem_candidate)
            final_result.extend(prefixes + suffix_processed)

        return final_result

    def split_prefix(self, token):
        token_lc = token.lower()
        if token_lc in kata_dasar:
            return [token]

        result = []
        current = token_lc
        while True:
            candidates = []
            sorted_prefixes = sorted(prefixes, key=len, reverse=True)
            for prefix in sorted_prefixes:
                if current.startswith(prefix):
                    stem_candidate = current[len(prefix):]
                    root_found = self._get_deep_root(stem_candidate)
                    if root_found:
                        candidates.append((prefix, root_found, stem_candidate))
            

            if candidates:
                best_match = max(candidates, key=lambda x: (len(x[1]), len(x[0])))
                chosen_prefix = best_match[0]
                current = best_match[2]
                result.append(chosen_prefix + '-')
                if current in kata_dasar:
                    break
            else:
                break

        result.append(current)
        return result

    def split_suffix(self, token):
        token_lc = token.lower()
            
        if token_lc in kata_dasar:
            return [token_lc]

        result = []
        current = token_lc

        while True:
            matched_suffix = None
            for suffix in sorted(suffixes, key=len, reverse=True):
                if current.endswith(suffix):
                    base_candidate = current[:-len(suffix)]
                    if base_candidate in kata_dasar:
                        matched_suffix = suffix
                        break 
                    
                    if matched_suffix is None and any(base_candidate.endswith(s) for s in suffixes):
                        matched_suffix = suffix

            if matched_suffix:
                result.insert(0, '-' + matched_suffix)
                current = current[:-len(matched_suffix)]
                if current in kata_dasar:
                    break
            else:
                break

        result.insert(0, current)  
        return result

    def split_particles(self, tokens):
        processed = []
        for token in tokens:
            matched = False
            for particle in sorted(particles, key=len, reverse=True):
                if token.endswith(particle):
                    root = token[:-len(particle)]
                    if len(root) > 1:
                        processed.append(root)
                        processed.append('-'+particle)  
                        matched = True
                        break
            if not matched:
                processed.append(token)
        return processed

class Checker:
    def __init__(self):
        self.kata_dasar = kata_dasar 

    def check_tokens(self, tokens):
        valid = []
        invalid = []

        for tok in tokens:
            clean = tok.lstrip('-')
            if all(c in string.punctuation for c in tok):
                continue

            if clean in kata_dasar:
                valid.append(tok)
                continue

            if clean in prefixes or clean in suffixes or clean in particles:
                valid.append(tok)
                continue

            invalid.append(tok)

        return valid, invalid

    def invalid_tokens(self, tokens):
        _, invalid = self.check_tokens(tokens)
        return invalid