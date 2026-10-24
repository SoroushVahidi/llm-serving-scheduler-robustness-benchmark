# Resume metadata correction

The pilot completed 12 cells in 0.974 s. The first continuation attempt
stopped before executing another cell: JSON converted the POLICIES tuple
to a list, so the in-memory identity comparison failed. The incomplete
analysis attempt also correctly refused the 12/72-cell artifact.

The correction normalizes metadata through JSON before comparing it.
It admits only the specifically pinned original runner hash as a compatible
predecessor; all protocol, input, policy, engine, referee, configuration and
condition identities still must agree. Original pilot cells and their
manifest are unchanged and their journals are revalidated on resume. New
cells and the continuation report record the actual corrected runner hash.
No simulator, policy, selected condition, outcome, or stopping rule changed.

Original runner SHA256: `03f942fbe016b3b270cab037156461c490ef44c2568b3e1908aa29c1f862ac68`.
The original code remains in preregistration commit 5630bfd. The failed
continuation log is retained outside Git beside the original pilot log.
