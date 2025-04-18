import numpy as np
from astropy.table import Table


def parse_sexa(string, hour=False):
    if not string:
        return np.nan

    sign = 1
    if string[0] in ['+', '-']:
        if string[0] == '-':
            sign = -1

        string = string[1:]

    s = [float(_) for _ in string.split()]
    scale = 15 if hour else 1

    return scale * sign * (s[0] + s[1]/60 + s[2]/3600)


def read_sips(filename, filled=False):
    with open(filename, 'r') as f:
        header = {}

        for i,line in enumerate(f):
            line = line.strip()
            # Format check
            if i == 0:
                if line != 'sep=;':
                    return None

            elif line.startswith('Name;'):
                # Header
                table = Table.read(
                    filename,
                    format='ascii',
                    header_start=i,
                    delimiter=';',
                    fill_values=(('', '0'), ('saturated', '0')),
                    converters={'Name': str},
                )
                table.meta.update(header)

                # Convert coordinates
                for __ in ('', 'Catalog'):
                    if (__ + 'RA') in table.colnames:
                        table[__ + 'RA'] = [parse_sexa(_, hour=True) for _ in table[__ + 'RA']]
                        table[__ + 'Dec'] = [parse_sexa(_) for _ in table[__ + 'Dec']]

                # Rename some columns
                table.rename_column('RA', 'ra')
                table.rename_column('Dec', 'dec')

                table.rename_column('X', 'x')
                table.rename_column('Y', 'y')

                # Adjust fill values for floating point columns
                for col in table.itercols():
                    if col.dtype.kind == 'f':
                        col.fill_value = np.nan

                if filled:
                    table = table.filled()

                return table

            else:
                s = line.split(';')
                if len(s) == 2:
                    val = s[1]

                    for t in (int, float):
                        try:
                            val = t(val)
                            break
                        except:
                            pass

                    header[s[0]] = val

    return None
