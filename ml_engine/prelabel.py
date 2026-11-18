"""Build a balanced review sample with rule-based DRAFT labels (no model used)."""
import pandas as pd

SRC = "ml_engine/data/eval/eval_to_label_clean.csv"
OUT = "ml_engine/data/eval/eval_review.csv"
PER_CLASS = 25
NET = ("Connection", "SSL", "MaxRetry", "NameResolution", "ProtocolError",
       "ReadTimeout", "ConnectTimeout")


def draft(text):
    etype, _, msg = text.partition(" ")
    short = etype.split(".")[-1]
    if len(msg.strip()) < 6 or "same traceback" in text or text.rstrip().endswith("..."):
        return "", "junk? truncated or empty"
    if short in ("AttributeError", "TypeError") and "NoneType" in msg:
        return "none_type_error", ""
    if short in ("SyntaxError", "IndentationError", "TabError"):
        return "syntax_error", ""
    simple = {"ModuleNotFoundError": "module_not_found", "FileNotFoundError": "file_not_found",
              "PermissionError": "permission_error", "KeyError": "key_error",
              "IndexError": "index_error", "AttributeError": "attribute_error",
              "TypeError": "type_error", "ValueError": "value_error"}
    if short in simple:
        return simple[short], ""
    if short == "ImportError":
        return "module_not_found", "check: ImportError (decide once, then be consistent)"
    if short == "OSError":
        if "No such file" in msg:
            return "file_not_found", ""
        if "Permission" in msg or "denied" in msg:
            return "permission_error", ""
        if "onnect" in msg or "route to host" in msg:
            return "network_error", ""
        return "other_error", "check: OSError"
    if any(k in short for k in NET):
        return "network_error", ""
    if short in ("TimeoutError", "HTTPError"):
        return "network_error", "check: is this really a network problem?"
    return "other_error", ""


df = pd.read_csv(SRC)
df[["label", "flag"]] = df["text"].apply(lambda t: pd.Series(draft(str(t))))
df = df[df["label"] != ""]                       # drop junk

# Shuffle once, then take the first PER_CLASS rows of each label.
df = df.sample(frac=1, random_state=42)
sample = df.groupby("label").head(PER_CLASS)

sample = sample.sort_values(["flag", "label"], ascending=[False, True])
sample[["text", "label", "flag"]].to_csv(OUT, index=False, encoding="utf-8")
print(sample["label"].value_counts().to_string())
print(f"\n{len(sample)} rows -> {OUT}  ({(sample['flag'] != '').sum()} flagged)")