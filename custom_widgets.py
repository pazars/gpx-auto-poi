import param
import panel as pn

from panel.viewable import Viewer


# class MultipleSwitches(Viewer):
#     num_switches = 2
#     value = param.List(item_type=bool)
#     # value = param.Range()

#     def __init__(self, **params):
#         self._first_switch = pn.widgets.Switch(value=False)
#         self._second_switch = pn.widgets.Switch(value=False)

#         super().__init__(**params)

#         self._layout = pn.Column(
#             self._first_switch,
#             self._second_switch,
#         )

#         self._sync_widgets()

#     def __panel__(self):
#         return self._layout

#     @param.depends("value", watch=True)
#     def _sync_widgets(self):
#         self._first_switch.value = self.value[0]
#         self._second_switch.value = self.value[1]

#     @param.depends("_first_switch.value", "_second_switch.value", watch=True)
#     def _sync_params(self):
#         self.value = [self._first_switch.value, self._second_switch.value]


class MultipleSwitches(pn.widgets.base.CompositeWidget):
    num_switches = 2
    value = param.List(default=[False] * num_switches, item_type=bool)

    _composite_type = pn.Column

    def __init__(self, **params):
        self._first_switch = pn.widgets.Switch()
        self._second_switch = pn.widgets.Switch()

        super().__init__(**params)

        self._composite[:] = [self._first_switch, self._second_switch]

        self._sync_widgets()

    @param.depends("value", watch=True)
    def _sync_widgets(self):
        self._first_switch.value = self.value[0]
        self._second_switch.value = self.value[1]

    @param.depends("_first_switch.value", "_second_switch.value", watch=True)
    def _sync_params(self):
        self.value = [self._first_switch.value, self._second_switch.value]


# single_switch = pn.widgets.Switch(value=False)
# multiple_switches = MultipleSwitches()


# def func_single(sw):
#     # sw is value of switch
#     return str(sw)


# def func_multiple(msw):
#     # msw is value of ?
#     return str(msw)


# pn.Column(
#     single_switch,
#     pn.bind(func_single, single_switch),
#     multiple_switches,
#     pn.bind(func_multiple, multiple_switches),
# ).servable()
