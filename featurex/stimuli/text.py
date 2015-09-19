from featurex.stimuli import Stim
from featurex.core import Timeline, Event, Value
import pandas as pd
from six import string_types
import re


class TextStim(Stim):

    ''' Any text stimulus. '''

    def __init__(self, filename=None, text=None):
        if filename is not None:
            text = open(filename).read()
        self.text = text

    def extract(self, extractors):
        vals = {}
        for e in extractors:
            vals[e.name] = e.apply(self)
        return Value(self, e, vals)


class DynamicTextStim(TextStim):

    ''' A text stimulus with timing/onset information. '''

    def __init__(self, text, order, onset=None, duration=None):
        self.order = order
        self.onset = onset
        self.duration = duration
        super(DynamicTextStim, self).__init__(text=text)


class ComplexTextStim(object):

    ''' A collection of text stims (e.g., a story), typically ordered and with
    onsets and/or durations associated with each element.
    Args:
        filename (str): The filename to read from. Must be tab-delimited text.
            Files must always contain a column containing the text of each
            stimulus in the collection. Optionally, additional columns can be
            included that contain duration and onset information. If a header
            row is present in the file, valid columns must be labeled as
            'text', 'onset', and 'duration' where available (though only text
            is mandatory). If no header is present in the file, the columns
            argument will be used to infer the indices of the key columns.
        columns (str): Optional specification of column order. An abbreviated
            string denoting the column position of text, onset, and duration
            in the file. Use t for text, o for onset, d for duration. For
            example, passing 'ot' indicates that the first column contains
            the onsets and the second contains the text. Passing 'tod'
            indicates that the first three columns contain text, onset, and
            duration information, respectively. Note that if the input file
            contains a header row, the columns argument will be ignored.
        default_duration (float): the duration to assign to any text elements
            in the collection that do not have an explicit value provided
            in the input file.
    '''

    def __init__(self, filename=None, columns='tod', default_duration=None):

        self.elements = []

        if filename is not None:
            self._from_file(filename, columns, default_duration)

    def _from_file(self, filename, columns, default_duration):
        tod_names = {'t': 'text', 'o': 'onset', 'd': 'duration'}

        first_row = open(filename).readline().strip().split('\t')
        if len(set(first_row) & set(tod_names.values())):
            col_names = None
        else:
            col_names = [tod_names[x] for x in columns]

        data = pd.read_csv(filename, sep='\t', names=col_names)

        for i, r in data.iterrows():
            if 'onset' not in r:
                elem = TextStim(r['text'])
            else:
                duration = r.get('duration', None)
                if duration is None:
                    duration = default_duration
                elem = DynamicTextStim(r['text'], i, r['onset'], duration)
            self.elements.append(elem)

    def __iter__(self):
        """ Iterate text elements. """
        for elem in self.elements:
            yield elem

    def extract(self, extractors, merge_events=True):
        timeline = Timeline()
        for ext in extractors:
            if ext.target.__name__ == self.__class__.__name__:
                events = ext.apply(self)
                for ev in events:
                    timeline.add_event(ev, merge=merge_events)
            else:
                for elem in self.elements:
                    event = Event(onset=elem.onset)
                    event.add_value(ext.apply(elem))
                    timeline.add_event(event, merge=merge_events)
        return timeline

    @classmethod
    def from_text(cls, text, unit='word', tokenizer=None, language='english'):
        """ Initialize from a single string, by automatically segmenting into
        individual strings. Requires nltk, unless unit == 'word' or an explicit
        tokenizer is passed.
        Args:
            text (str): The text to convert to a ComplexTextStim.
            unit (str): The unit of segmentation. Either 'word' or 'sentence'.
            tokenizer: Optional tokenizer to use (will override unit).
                If a string is passed, it is interpreted as a capturing regex
                and passed to re.findall(). Otherwise, must be a
                nltk Tokenizer instance.
            language (str): The language to use. Only used if tokenizer is
                None and nltk is installed. Defaults to English.
        Returns:
            A ComplexTextStim instance.
        """

        if tokenizer is not None:
            if isinstance(tokenizer, string_types):
                tokens = re.findall(tokenizer, text)
            else:
                tokens = tokenizer.tokenize(text)
        else:
            try:
                import nltk
                try:
                    nltk.data.find('punkt.zip')
                except LookupError:
                    nltk.download('punkt')
                if unit == 'word':
                    tokens = nltk.word_tokenize(text, language)
                elif unit.startswith('sent'):
                    tokens = nltk.sent_tokenize(text, language)
                else:
                    raise ValueError(
                        "unit must be either 'word' or 'sentence'")
            except:
                if unit != 'word':
                    raise ImportError("If no tokenizer is passed and nltk is "
                                      "not installed, unit must be set to "
                                      " 'word'.")
                # Could be improved, but should really use nltk anyway
                patt = "[A-Z\-\']{2,}(?![a-z])|[A-Z\-\'][a-z\-\']+(?=[A-Z])|[\'\w\-]+"
                tokens = re.findall(patt, text)

        cts = ComplexTextStim()
        for t in tokens:
            cts.elements.append(TextStim(text=t))
        return cts
