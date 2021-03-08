import re
from rig.config import Config

class Naming(object):
    # Default configuration
    CONFIG = Config
    NODETYPE = None

    def __init__(self, 
                 name, 
                 node_type=None, 
                 role=None, 
                 descriptor=None, 
                 region=None, 
                 side=None):
        
        self._name = name
        self._node_type = node_type
        self._role = role
        self._descriptor = descriptor
        self._region = region
        self._side = side
        self.delimiter = self.CONFIG.DELIMITER
        
        # Try to pop name components
        if not any(k for k in [node_type, role, descriptor, region, side]):
            self.decompose_name()

    def decompose_name(self):
        """
        Decompose name and populate class variables from therein
        """
        tokens = self.tokens

        if len(tokens) == len(self.CONFIG.TokenOrder):
            for key, token in zip(self.CONFIG.TokenOrder, tokens):
                setattr(self, '_{}'.format(key), token)
        
        # Otherwise, let's go one by one to match
        # tokens to properties
        for token in tokens[:]:
            if any(token == val for val in self.CONFIG.SIDES.values()):
                self._side = token
                tokens.remove(token)
            
            elif any(token == val for val in self.CONFIG.REGIONS.values()):
                self._region = token
                tokens.remove(token)
            
            elif any(token == val for val in self.CONFIG.NODETYPES.values()):
                self._node_type = token
                tokens.remove(token)
        
        # The rest of the tokens are arbitrary in values
        if len(tokens) == 1:
            self._descriptor = tokens[0]
        
        elif len(tokens) == 2:
            order = list(tok for tok in self.CONFIG.TokenOrder if tok in ['role', 'descriptor'])
            while tokens:
                for token in order:
                    setattr(self, '_{}'.format(token), tokens[0])
                    tokens.remove(tokens[0])

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name

    def as_dict(self):
        return dict(node_type=self._node_type, 
                    role=self._role, 
                    descriptor=self._descriptor, 
                    region=self._region, 
                    side=self._side)

    @property
    def tokens(self):
        return self._name.split(self.delimiter)

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, new_name):
        if new_name == self._name:
            return
        else:
            self._name = new_name

    @property
    def node_type(self):
        return self._node_type
    
    @node_type.setter
    def node_type(self, new_type):
        if new_type == self._node_type:
            return
        else:
            self._node_type = self.CONFIG.NODETYPES.get(new_type, new_type)
            self.name = self.compose_name(**self.as_dict())

    @property
    def side(self):
        """
        Returns the side, typically representing one of three options:
        left, center, or right
        """
        # Otherwise let's find the side
        if not self._side:
            for token in self.CONFIG.SIDES.values():
                pattern = re.escape(self.CONFIG.DELIMITER + token) + r'\d?'
                matcher = re.compile(pattern, flags=re.IGNORECASE)
                match = matcher.search(self.name)
                if match:
                    self._side = match.group(0)
                    break
        return self._side
    
    @side.setter
    def side(self, new_side):
        # If side is the same, return now
        if new_side == self._side:
            return
        else:
            self._side = self.CONFIG.SIDES.get(new_side, new_side)
            self.name = self.compose_name(**self.as_dict())

    @property
    def region(self):
        """
        A region can be typically used to describe a location
        not covered by the sides (left, center, right)

        For example:
            top, bottom, outside, inside
        """
        # Otherwise let's find the region
        if not self._region:
            for token in self.CONFIG.REGIONS.values():
                pattern = re.escape(self.CONFIG.DELIMITER + token) + r'\d?'
                matcher = re.compile(pattern, flags=re.IGNORECASE)
                match = matcher.search(self.name)
                if match:
                    self._region = match.group(0)
                    break
        
        return self._region
    
    @region.setter
    def region(self, new_region):
        if new_region == self._region:
            return
        else:
            self._region = new_region
            self._name = self.compose_name(**self.as_dict())

    @property
    def descriptor(self):
        """
        The descriptor is completely arbitrary, and can be numbered,
        for example:
            elbow01, elbow02, thigh03
        """
        return self._descriptor
    
    @descriptor.setter
    def descriptor(self, new_descriptor):
        # If the new descriptor is the same, return
        if new_descriptor == self._descriptor:
            return
        else:
            self._descriptor = new_descriptor
            self._name = self.compose_name(**self.as_dict())

    @property
    def role(self):
        """
        A role can be used to hint at the use of an object
        for example, a joint can be used for:
            - deformation
            - rolling/twisting
            - pivot
        """
        return self._role
    
    @role.setter
    def role(self, new_role):
        if new_role == self._role:
            return
        else:
            self._role = new_role
            self._name = self.compose_name(**self.as_dict())

    @classmethod
    def compose_name(cls, **kwargs):
        """
        Get a name with consistent order of tokens,
        for example, given this call:
            Naming.compose(node_type='joint', role='def', descriptor='lip', region='top', side='left')

        And this token order:
            node_type, role, descriptor, region, side

        Will output:
            jnt_def_lip_tp_l
        
        :keyword str node_type:
        :keyword str role:
        :keyword str descriptor:
        :keyword str region:
        :keyword str side:
        :returns str name: new name composed from keyword arguments
        """
        
        new_name = list()
        
        # If no node_type value passed, use class variable
        if not kwargs.get('node_type', None):
            kwargs.update(dict(node_type=cls.NODETYPE))

        # Search our TokenOrder dictionary to compose a name
        # in that order, and use internal mapping to shorten strings
        # and follow conventions
        for token in cls.CONFIG.TokenOrder:
            if token in kwargs:
                if not kwargs.get(token, None):
                    continue
                v = kwargs[token]
                token_name = cls.CONFIG.TokenOrder[token].get(v, v)
                new_name.append(token_name)
        
        return cls.CONFIG.DELIMITER.join(new_name)

    @classmethod
    def compose(cls, **kwargs):
        """
        Get a name with consistent order of tokens,
        for example, given this call:
            Naming.compose(node_type='joint', role='def', descriptor='lip', region='top', side='left')

        And this token order:
            node_type, role, descriptor, region, side

        Will output:
            jnt_def_lip_tp_l
        
        :keyword str node_type:
        :keyword str role:
        :keyword str descriptor:
        :keyword str region:
        :keyword str side:
        :returns naming: a class instance with the new name
        :rtype Naming:
        """
        name = cls.compose_name(**kwargs)
        return cls(name, **kwargs)