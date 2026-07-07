# ==========================================================
# BASE REVIEWER
# ==========================================================

from abc import ABC, abstractmethod


class BaseReviewer(ABC):

    # ======================================================
    # GENERATE REVIEW
    # ======================================================

    @abstractmethod
    def generate_review(

        self,

        prompt
    ):

        pass