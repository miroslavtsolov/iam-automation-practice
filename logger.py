import logging

def get_logger():
    logging.basicConfig(
        filename="iam_review.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger("iam_review")
