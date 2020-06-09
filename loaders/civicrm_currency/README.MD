# Currency data loader

To be able to calculate value of multi-currency donations, currency conversion
data is needed. This loader lives in a separate directory because currency is
not exactly CRM data, it is treated as a separate data source.

In WeMove, it happens that CiviCRM contains tables with recent, approximate
exchange rates, and for the MVP we are using them. However, a btter solution
should be implemented - the one that contains historical exchange rate, so value
of historical donations can be accurately calculated.
