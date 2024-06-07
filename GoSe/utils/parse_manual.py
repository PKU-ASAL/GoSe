import logging
import os

def parse_manual(prog_path, manual_text, dest_dir):
    logging.debug("Parsing manual for program: {}".format(prog_path))
    assert manual_text is not None and len(manual_text) > 0
    prog_name = os.path.basename(prog_path)
    # make sure dest_dir exists
    assert dest_dir is not None and len(dest_dir) > 0
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    # ...
    assert False, "Need to implement"
