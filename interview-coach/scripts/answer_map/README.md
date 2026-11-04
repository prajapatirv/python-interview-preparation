# Interview Answer Map: page build

Builds the single-page Interview Answer Map: the reported questions, plans by experience and full
answers, as one HTML file with no server. It reads the same banks and tracks as the coach.

```bash
cd interview-coach
.venv/Scripts/pip install -r requirements-dev.txt   # markdown-it-py renders the answers
.venv/Scripts/python.exe scripts/answer_map/build.py
```

The page lands in `out/interview-answer-map.html`. `out/` is gitignored, so the page is rebuilt, not stored.

## Adding answers to the page

An answer goes on the page only after someone has read it. Banks can hold personal or
company-specific text that suits the coach but not a page other people will read.

1. Build. `out/unread.txt` holds the full text of every plan question not yet on the page, and
   `out/unread.json` holds their ids.
2. Read the text. Leave out anything personal or company-specific.
3. Fix real errors in the bank file. Put wording that is only wrong on this page in `TIDY` in `build.py`.
4. Save the approved ids as `reviewed/batchN.json`, then build again.

The build prints what to check: plan anchors without an answer, dead in-page links and leftover
words. All three lists should be empty or match what you expect. Private words to check for go in
`out/banned.txt`, one per line, which git ignores. Retitling a question changes its
id, so `tests/test_real_repo.py` fails until the id in `reviewed/` is updated.
