##########################################################################################
# errors.py
##########################################################################################
"""Exception types shared by the target-identification modules."""

__all__ = ['TargetIdentificationError']


class TargetIdentificationError(ValueError):
    """Raised when no target can be identified for an observation, or when a target
    identified by name is incompatible with the orbital elements in the header.
    """

##########################################################################################
