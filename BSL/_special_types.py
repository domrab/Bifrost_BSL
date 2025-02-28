
class AddableDict(dict):
    def __init__(self, d=None, **kwargs):
        super().__init__()
        for key, value in (d or {}).items():
            self[key] = value

        for key, value in kwargs.items():
            self[key] = value

    def __add__(self, cfg):
        return self.__class__(self, **cfg)


class Namespaces(AddableDict):
    def __getitem__(self, item):
        if item not in self:
            for s in self.keys():
                if s.endswith("::" + item):
                    item = s
                    break
            else:
                raise KeyError(f"Missing '{item}'. Available: {list(self.keys())}")

        return super().__getitem__(item)

    def resolves(self, item):
        if item not in self:
            for s in self.keys():
                if s.endswith("::" + item):
                    return s
            else:
                return False
        return item


class Port(AddableDict):
    def __getitem__(self, item):
        item_alt = "port" + item[0].upper() + item[1:]
        if item not in self:
            if item_alt in self:
                item = item_alt
            else:
                raise KeyError(f"Missing '{item}/{item_alt}'. Available: {list(self.keys())}")
        return super().__getitem__(item)

    @classmethod
    def from_list(cls, da_ports, direction="*"):
        d_ports = AddableDict()
        for d in da_ports:
            if direction == "*" or d["portDirection"] == direction:
                d_ports += {d["portName"]: Port(d)}
        return d_ports


class Metadata(AddableDict):
    def __getitem__(self, item):
        item_alt = "meta" + item[0].upper() + item[1:]
        if item not in self:
            if item_alt in self:
                item = item_alt
            else:
                raise KeyError(f"Missing '{item}/{item_alt}'. Available: {list(self.keys())}")
        return super().__getitem__(item)

    @classmethod
    def from_list(cls, da_metadata):
        d_metadata = AddableDict()
        for d in da_metadata:
            d_metadata += {d["metaName"]: Metadata.from_list(d["metadata"]) if "metadata" in d else Metadata(d)}

        return d_metadata


class ParserDict(dict):
    ...
