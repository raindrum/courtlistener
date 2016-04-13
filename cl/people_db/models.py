from django.core.urlresolvers import reverse
from django.db import models
from django.utils.text import slugify
from localflavor.us import models as local_models
from cl.lib.model_helpers import (
    make_choices_group_lookup,
    validate_has_full_name,
    validate_is_not_alias,
    validate_partial_date,
    validate_nomination_fields_ok,
    validate_all_or_none,
    validate_exactly_n,
    validate_not_all,
    validate_at_most_n)
from cl.lib.string_utils import trunc
from cl.search.models import Court

SUFFIXES = (
    ('jr', 'Jr.'),
    ('sr', 'Sr.'),
    ('1', 'I'),
    ('2', 'II'),
    ('3', 'III'),
    ('4', 'IV'),
)
GENDERS = (
    ('m', 'Male'),
    ('f', 'Female'),
    ('o', 'Other'),
)
GRANULARITY_YEAR = '%Y'
GRANULARITY_MONTH = '%Y-%m'
GRANULARITY_DAY = '%Y-%m-%d'
DATE_GRANULARITIES = (
    (GRANULARITY_YEAR, 'Year'),
    (GRANULARITY_MONTH, 'Month'),
    (GRANULARITY_DAY, 'Day'),
)


class Person(models.Model):
    RELIGIONS = (
        ('ca', 'Catholic'),
        ('pr', 'Protestant'),
        ('je', 'Jewish'),
        ('mu', 'Muslim'),
        ('at', 'Atheist'),
        ('ag', 'Agnostic'),
        ('mo', 'Mormon'),
        ('bu', 'Buddhist'),
        ('hi', 'Hindu')
    )
    race = models.ManyToManyField(
        'Race',
        blank=True,
    )
    is_alias_of = models.ForeignKey(
        'self',
        related_name="aliases",
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    fjc_id = models.IntegerField(
        help_text="The ID of a judge as assigned by the Federal Judicial "
                  "Center.",
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    cl_id = models.CharField(
        max_length=30,
        help_text="A unique identifier for judge, also indicating source of "
                  "data.",
        unique=True,
        db_index=True
    )
    slug = models.SlugField(
        max_length=158  # len(self.name_full)
    )
    name_first = models.CharField(
        max_length=50,
    )
    name_middle = models.CharField(
        max_length=50,
        blank=True,
    )
    name_last = models.CharField(
        max_length=50,
        db_index=True,
    )
    name_suffix = models.CharField(
        choices=SUFFIXES,
        max_length=5,
        blank=True,
    )
    date_dob = models.DateField(
        null=True,
        blank=True,
    )
    date_granularity_dob = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
        blank=True,
    )
    date_dod = models.DateField(
        null=True,
        blank=True,
    )
    date_granularity_dod = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
        blank=True,
    )
    dob_city = models.CharField(
        max_length=50,
        blank=True,
    )
    dob_state = local_models.USStateField(
        blank=True,
    )
    dod_city = models.CharField(
        max_length=50,
        blank=True,
    )
    dod_state = local_models.USStateField(
        blank=True,
    )
    gender = models.CharField(
        choices=GENDERS,
        max_length=2,
        blank=True,
    )
    religion = models.CharField(
        choices=RELIGIONS,
        max_length=2,
        blank=True
    )
    has_photo = models.BooleanField(
        help_text="Whether there is a photo corresponding to this person in "
                  "the judge pics project.",
        default=False,
    )

    def __unicode__(self):
        return u'%s: %s' % (self.pk, self.name_full)

    def get_absolute_url(self):
        return reverse('view_person', args=[self.pk, self.slug])

    def save(self, *args, **kwargs):
        self.slug = slugify(trunc(self.name_full, 158))
        self.full_clean()
        super(Person, self).save(*args, **kwargs)

    def clean_fields(self, *args, **kwargs):
        validate_partial_date(self, ['dob', 'dod'])
        validate_is_not_alias(self, ['is_alias_of'])
        validate_has_full_name(self)
        super(Person, self).clean_fields(*args, **kwargs)

    @property
    def name_full(self):
        return u' '.join([v for v in [
            self.name_first,
            self.name_middle,
            self.name_last,
            self.get_name_suffix_display(),
        ] if v]).strip()

    @property
    def name_full_reverse(self):
        return u'{name_last}, {name_first} {name_middle}, {suffix}'.format(
            suffix=self.get_name_suffix_display(),
            **self.__dict__
        ).strip(', ')

    @property
    def is_alias(self):
        return True if self.is_alias_of is not None else False

    @property
    def is_judge(self):
        """Examine the positions a person has had and identify if they were ever
        a judge.
        """
        for position in self.positions.all():
            if position.is_judicial_position:
                return True
        return False

    class Meta:
        verbose_name_plural = "people"


class School(models.Model):
    is_alias_of = models.ForeignKey(
        'self',
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified",
        auto_now=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=120,  # Dept. Ed. bulk data had a max of 91.
        db_index=True,
    )
    ein = models.IntegerField(
        help_text="The EIN assigned by the IRS",
        null=True,
        blank=True,
        db_index=True,
    )

    def __unicode__(self):
        if self.is_alias_of:
            return u'%s: %s (alias: %s)' % (
                self.pk, self.name, self.is_alias_of.name
            )
        else:
            return u'%s: %s' % (
                self.pk, self.name
            )

    @property
    def is_alias(self):
        return True if self.is_alias_of is not None else False

    def clean_fields(self, *args, **kwargs):
        # An alias cannot be an alias.
        validate_is_not_alias(self, ['is_alias_of'])
        super(School, self).clean_fields(*args, **kwargs)


class Position(models.Model):
    """A role held by a person, and the details about it."""
    POSITION_TYPES = (
        ('Judge', (
            # Acting
            ('act-jud',      'Acting Judge'),
            ('act-pres-jud', 'Acting Presiding Judge'),

            # Associate
            ('ass-jud',      'Associate Judge'),
            ('ass-c-jud',    'Associate Chief Judge'),
            ('ass-pres-jud', 'Associate Presiding Judge'),
            ('jud',          'Judge'),
            ('jus',          'Justice'),

            # Chief
            ('c-jud',     'Chief Judge'),
            ('c-jus',     'Chief Justice'),
            ('pres-jud',  'Presiding Judge'),
            ('pres-jus',  'Presiding Justice'),
            ('pres-mag',  'Presiding Magistrate'),
            # Commissioner
            ('com',     'Commissioner'),
            ('com-dep', 'Deputy Commissioner'),

            # Pro Tem
            ('jud-pt', 'Judge Pro Tem'),
            ('jus-pt', 'Justice Pro Tem'),
            ('mag-pt', 'Magistrate Pro Tem'),

            # Referee
            ('ref-jud-tr',      'Judge Trial Referee'),
            ('ref-off',         'Official Referee'),
            ('ref-state-trial', 'State Trial Referee'),

            # Retired
            ('ret-act-jus',    'Active Retired Justice'),
            ('ret-ass-jud',    'Retired Associate Judge'),
            ('ret-c-jud',      'Retired Chief Judge'),
            ('ret-jus',        'Retired Justice'),
            ('ret-senior-jud', 'Senior Judge'),

            # Special
            ('spec-chair',  'Special Chairman'),
            ('spec-jud',    'Special Judge'),
            ('spec-m',      'Special Master'),
            ('spec-scjcbc', 'Special Superior Court Judge for Complex Business '
                            'Cases'),
            # Other
            ('chair',     'Chairman'),
            ('chan',      'Chancellor'),
            ('mag',       'Magistrate'),
            ('presi-jud', 'President'),
            ('res-jud',   'Reserve Judge'),
            ('trial-jud', 'Trial Judge'),
            ('vice-chan', 'Vice Chancellor'),
            ('vice-cj',   'Vice Chief Judge'),
        )),
        # Sometimes attorney generals write opinions too
        ('Attorney General', (
            ('att-gen',          'Attorney General'),
            ('att-gen-ass',      'Assistant Attorney General'),
            ('att-gen-ass-spec', 'Special Assistant Attorney General'),
            ('sen-counsel',      'Senior Counsel'),
            ('dep-sol-gen',      'Deputy Solicitor General'),
        )),
        ('Appointing Authority', (
            ('pres',          'President of the United States'),
            ('gov',           'Governor'),
        )),
        ('Clerkships', (
            ('clerk',      'Clerk'),
            ('staff-atty', 'Staff Attorney'),
        )),

        ('prof',    'Professor'),
        ('prac',    'Practitioner'),
        ('pros',    'Prosecutor'),
        ('pub_def', 'Public Defender'),
        ('legis',   'Legislator'),
    )
    POSITION_TYPE_GROUPS = make_choices_group_lookup(POSITION_TYPES)
    NOMINATION_PROCESSES = (
        ('fed_senate', 'U.S. Senate'),
        ('state_senate', 'State Senate'),
        ('election', 'Primary Election'),
        ('merit_comm', 'Merit Commission'),
    )
    VOTE_TYPES = (
        ('s', 'Senate'),
        ('p', 'Partisan Election'),
        ('np', 'Non-Partisan Election'),
    )
    JUDICIAL_COMMITTEE_ACTIONS = (
        ('no_rep', 'Not Reported'),
        ('rep_w_rec', 'Reported with Recommendation'),
        ('rep_wo_rec', 'Reported without Recommendation'),
        ('rec_postpone', 'Recommendation Postponed'),
        ('rec_bad', 'Recommended Unfavorably'),
    )
    SELECTION_METHODS = (
        ('Election', (
            ('e_part', 'Partisan Election'),
            ('e_non_part', 'Non-Partisan Election'),

        )),
        ('Appointment', (
            ('a_pres', 'Appointment (President)'),
            ('a_gov', 'Appointment (Governor)'),
            ('a_legis', 'Appointment (Legislature)'),
        )),
    )
    SELECTION_METHOD_GROUPS = make_choices_group_lookup(SELECTION_METHODS)
    TERMINATION_REASONS = (
        ('ded', 'Death'),
        ('retire_vol', 'Voluntary Retirement'),
        ('retire_mand', 'Mandatory Retirement'),
        ('resign', 'Resigned'),
        ('other_pos', 'Appointed to Other Judgeship'),
        ('lost', 'Lost Election'),
        ('abolished', 'Court Abolished'),
        ('bad_judge', 'Impeached and Convicted'),
        ('recess_not_confirmed', 'Recess Appointment Not Confirmed'),
    )
    position_type = models.CharField(
        choices=POSITION_TYPES,
        max_length=20,
        blank=True,
        null=True,
    )
    job_title = models.CharField(
        help_text="If title isn't in list, type here.",
        max_length=100,
        blank=True,
    )
    person = models.ForeignKey(
        Person,
        related_name='positions',
        blank=True,
        null=True,
    )
    court = models.ForeignKey(
        Court,
        related_name='court_positions',
        blank=True,
        null=True,
    )
    school = models.ForeignKey(
        School,
        help_text="If academic job, the school where they work.",
        blank=True,
        null=True,
    )
    organization_name = models.CharField(
        help_text="If org isn't court or school, type here.",
        max_length=120,
        blank=True,
        null=True,
    )
    appointer = models.ForeignKey(
        Person,
        related_name='appointed_positions',
        help_text="If this is an appointed position, "
                  "the person responsible for the appointing.",
        blank=True,
        null=True,
    )
    supervisor = models.ForeignKey(
        Person,
        related_name='supervised_positions',
        help_text="If this is a clerkship, the supervising judge.",
        blank=True,
        null=True,
    )
    predecessor = models.ForeignKey(
        Person,
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The time when this item was created",
        auto_now_add=True,
        db_index=True,
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    date_nominated = models.DateField(
        help_text="The date recorded in the Senate Executive Journal when a "
                  "federal judge was nominated for their position or the date "
                  "a state judge nominated by the legislature. When a "
                  "nomination is by primary election, this is the date of the "
                  "election. When a nomination is from a merit commission, "
                  "this is the date the nomination was announced.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_elected = models.DateField(
        help_text="Judges are elected in most states. This is the date of their"
                  "first election. This field will be null if the judge was "
                  "initially selected by nomination.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_recess_appointment = models.DateField(
        help_text="If a judge was appointed while congress was in recess, this "
                  "is the date of that appointment.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_referred_to_judicial_committee = models.DateField(
        help_text="Federal judges are usually referred to the Judicial "
                  "Committee before being nominated. This is the date of that "
                  "referral.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_judicial_committee_action = models.DateField(
        help_text="The date that the Judicial Committee took action on the "
                  "referral.",
        null=True,
        blank=True,
        db_index=True,
    )
    judicial_committee_action = models.CharField(
        choices=JUDICIAL_COMMITTEE_ACTIONS,
        max_length=20,
        blank=True,
    )
    date_hearing = models.DateField(
        help_text="After being nominated, a judge is usually subject to a "
                  "hearing. This is the date of that hearing.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_confirmation = models.DateField(
        help_text="After the hearing the senate will vote on judges. This is "
                  "the date of that vote.",
        null=True,
        blank=True,
        db_index=True,
    )
    date_start = models.DateField(
        help_text="The date the position starts active duty.",
        db_index=True,
    )
    date_granularity_start = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
    )
    date_termination = models.DateField(
        help_text="The last date of their employment. The compliment to "
                  "date_start",
        null=True,
        blank=True,
        db_index=True,
    )
    termination_reason = models.CharField(
        choices=TERMINATION_REASONS,
        max_length=25,
        blank=True,
    )
    date_granularity_termination = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
        blank=True,
    )
    date_retirement = models.DateField(
        help_text="The date when they become a senior judge by going into "
                  "active retirement",
        null=True,
        blank=True,
        db_index=True,
    )
    nomination_process = models.CharField(
        choices=NOMINATION_PROCESSES,
        max_length=20,
        blank=True,
    )
    vote_type = models.CharField(
        choices=VOTE_TYPES,
        max_length=2,
        blank=True,
    )
    voice_vote = models.NullBooleanField(
        blank=True,
    )
    votes_yes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    votes_no = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    votes_yes_percent = models.FloatField(
        null=True,
        blank=True,
    )
    votes_no_percent = models.FloatField(
        null=True,
        blank=True,
    )
    how_selected = models.CharField(
        choices=SELECTION_METHODS,
        max_length=20,
        blank=True,
    )

    def __unicode__(self):
        return u'%s: %s at %s' % (self.pk, self.person.name_full, self.court_id)

    @property
    def is_judicial_position(self):
        """Return True if the position is judicial."""
        if self.POSITION_TYPE_GROUPS[self.position_type] == 'Judge':
            return True
        return False

    @property
    def vote_string(self):
        """Make a human-friendly string from the vote information"""
        vote_string = ''

        # Do vote type first
        if self.vote_type == 's':
            vote_string += "Senate voted"
            if self.voice_vote:
                vote_string += ' <span class="alt">by</span> voice vote'
        elif self.vote_string in ['p', 'np']:
            vote_string += self.get_vote_type_display()

        # Then do vote counts/percentages, if we have that info.
        if self.votes_yes:
            vote_string += ', %s in favor <span class="alt">and</span> %s ' \
                           'opposed' % (self.votes_yes, self.votes_no)
        elif self.votes_yes_percent:
            vote_string += ', %g%% in favor <span class="alt">and</span> ' \
                           '%g%% opposed' % (self.votes_yes_percent,
                                             self.votes_no_percent)
        return vote_string

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Position, self).save(*args, **kwargs)

    def clean_fields(self, *args, **kwargs):
        validate_partial_date(self, ['start', 'termination'])
        validate_is_not_alias(self, ['person', 'appointer', 'supervisor',
                                     'predecessor', 'school'])
        validate_at_most_n(self, 1, ['school', 'organization_name', 'court'])
        validate_exactly_n(self, 1, ['position_type', 'job_title'])
        validate_nomination_fields_ok(self)
        validate_all_or_none(self, ['votes_yes', 'votes_no'])
        validate_all_or_none(self, ['votes_yes_percent', 'votes_no_percent'])
        validate_not_all(self, ['votes_yes', 'votes_no', 'votes_yes_percent',
                                'votes_no_percent'])

        super(Position, self).clean_fields(*args, **kwargs)


class RetentionEvent(models.Model):
    RETENTION_TYPES = (
        ('reapp_gov', 'Governor Reappointment'),
        ('reapp_leg', 'Legislative Reappointment'),
        ('elec_p', 'Partisan Election'),
        ('elec_n', 'Nonpartisan Election'),
        ('elec_u', 'Uncontested Election'),
    )
    position = models.ForeignKey(
        Position,
        related_name='retention_events',
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    retention_type = models.CharField(
        choices=RETENTION_TYPES,
        max_length=10,
    )
    date_retention = models.DateField(
        db_index=True,
    )
    votes_yes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    votes_no = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    votes_yes_percent = models.FloatField(
        null=True,
        blank=True,
    )
    votes_no_percent = models.FloatField(
        null=True,
        blank=True,
    )
    unopposed = models.NullBooleanField(
        null=True,
        blank=True,
    )
    won = models.NullBooleanField(
        null=True,
        blank=True,
    )

    def clean_fields(self, *args, **kwargs):
        validate_all_or_none(self, ['votes_yes', 'votes_no'])
        validate_all_or_none(self, ['votes_yes_percent', 'votes_no_percent'])
        super(RetentionEvent, self).clean_fields(*args, **kwargs)


class Education(models.Model):
    DEGREE_LEVELS = (
        ('ba', "Bachelor's (e.g. B.A.)"),
        ('ma', "Master's (e.g. M.A.)"),
        ('jd', 'Juris Doctor (J.D.)'),
        ('llm', 'Master of Laws (LL.M)'),
        ('llb', 'Bachelor of Laws (e.g. LL.B)'),
        ('jsd', 'Doctor of Law (J.S.D)'),
        ('phd', 'Doctor of Philosophy (PhD)'),
        ('aa', 'Associate (e.g. A.A.)'),
        ('md', 'Medical Degree (M.D.)'),
        ('mba', 'Master of Business Administration (M.B.A.)')
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    person = models.ForeignKey(
        Person,
        related_name='educations',
        blank=True,
        null=True,
    )
    school = models.ForeignKey(
        School,
        related_name='educations',
    )
    degree_level = models.CharField(
        choices=DEGREE_LEVELS,
        max_length=3,
        blank=True,
    )
    degree_detail = models.CharField(
        max_length=100,
        blank=True,
    )
    degree_year = models.PositiveSmallIntegerField(
        help_text="The year the degree was awarded.",
        null=True,
        blank=True,
    )

    def __unicode__(self):
        return u'%s: Degree in %s from %s in the year %s' % (
            self.pk, self.degree_detail, self.school.name, self.degree_year
        )

    def clean_fields(self, *args, **kwargs):
        # Note that this isn't run during updates, alas.
        validate_is_not_alias(self, ['person', 'school'])
        validate_all_or_none(self, ['degree_detail', 'degree_level'])
        super(Education, self).clean_fields(*args, **kwargs)


class Race(models.Model):
    RACES = (
        ('w', 'White'),
        ('b', 'Black or African American'),
        ('i', 'American Indian or Alaska Native'),
        ('a', 'Asian'),
        ('p', 'Native Hawaiian or Other Pacific Islander'),
        ('h', 'Hispanic/Latino'),
    )
    race = models.CharField(
        choices=RACES,
        max_length=5,
        unique=True,
    )

    def __unicode__(self):
        # This is used in the API via the StringRelatedField. Do not cthange.
        return u"{race}".format(race=self.race)


class PoliticalAffiliation(models.Model):
    POLITICAL_AFFILIATION_SOURCE = (
        ('b', 'Ballot'),
        ('a', 'Appointer'),
        ('o', 'Other'),
    )
    POLITICAL_PARTIES = (
        ('d', 'Democrat'),
        ('r', 'Republican'),
        ('i', 'Independent'),
        ('g', 'Green'),
        ('l', 'Libertarian'),
        ('f', 'Federalist'),
        ('w', 'Whig'),
        ('j', 'Jeffersonian Republican')
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    person = models.ForeignKey(
        Person,
        related_name='political_affiliations',
        blank=True,
        null=True,
    )
    political_party = models.CharField(
        choices=POLITICAL_PARTIES,
        max_length=5,
    )
    source = models.CharField(
        choices=POLITICAL_AFFILIATION_SOURCE,
        max_length=5,
        blank=True,
    )
    date_start = models.DateField(
        null=True,
        blank=True,
    )
    date_granularity_start = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
        blank=True,
    )
    date_end = models.DateField(
        null=True,
        blank=True,
    )
    date_granularity_end = models.CharField(
        choices=DATE_GRANULARITIES,
        max_length=15,
        blank=True,
    )

    def clean_fields(self, *args, **kwargs):
        validate_partial_date(self, ['start', 'end'])
        validate_is_not_alias(self, ['person'])
        super(PoliticalAffiliation, self).clean_fields(*args, **kwargs)


class Source(models.Model):
    person = models.ForeignKey(
        Person,
        related_name='sources',
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified",
        auto_now=True,
        db_index=True,
    )
    url = models.URLField(
        help_text="The URL where this data was gathered.",
        max_length=2000,
        blank=True,
    )
    date_accessed = models.DateField(
        help_text="The date the data was gathered.",
        blank=True,
        null=True,
    )
    notes = models.TextField(
        help_text="Any additional notes about the data's provenance, in "
                  "Markdown format.",
        blank=True,
    )


class ABARating(models.Model):
    ABA_RATINGS = (
        ('ewq', 'Exceptionally Well Qualified'),
        ('wq', 'Well Qualified'),
        ('q', 'Qualified'),
        ('nq', 'Not Qualified'),
        ('nqa', 'Not Qualified By Reason of Age'),
    )
    person = models.ForeignKey(
        Person,
        related_name='aba_ratings',
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(
        help_text="The original creation date for the item",
        auto_now_add=True,
        db_index=True
    )
    date_modified = models.DateTimeField(
        help_text="The last moment when the item was modified.",
        auto_now=True,
        db_index=True,
    )
    year_rated = models.PositiveSmallIntegerField(
        help_text="The year of the rating.",
        null=True
    )
    rating = models.CharField(
        choices=ABA_RATINGS,
        max_length=5,
    )

    class Meta:
        verbose_name = 'American Bar Association Rating'
        verbose_name_plural = 'American Bar Association Ratings'

    def clean_fields(self, *args, **kwargs):
        validate_is_not_alias(self, ['person'])
        super(ABARating, self).clean_fields(*args, **kwargs)
