import pytest, sys
from fenicsbot.fenicsbot import FEniCSbot


SOLUTION_TWEET = "tweeting solution"
ERROR_TWEET = "tweeting error "
EXIT_EXCEPTION_MESSAGE = "Exception raised to stop FEniCSbot main loop"
SLEEP_TIME = 1                # testing is too important to wait!

class DummyTweet():
    """Dummy Twitter status object."""
    id_counter = 10
    def __init__(self, tweet_text):
        self.text = tweet_text

        #all tweets are recent
        self.id = DummyTweet.id_counter
        DummyTweet.id_counter += 1
        self.created_at_in_seconds = sys.maxint

        class DummyUser():
            def __init__(self):
                self.screen_name = "DummyUser"

        self.user = DummyUser()

class DummyTwitterApi():
    """
    dummy Twitter API for tricking FEniCSbot
    into believing it is doing something meaningful
    """
    def __init__(self, mentions_batches):
        self.tweets = []
        self.mentions = map(lambda l: map(DummyTweet, l),
                            mentions_batches)
        # print self.mentions
        self.is_empty = lambda : len(self.mentions) == 0

    def dummy_tweet(self, tweet_text):
        # print tweet_text
        self.tweets.append(tweet_text)

    def PostMedia(self, *args, **kwargs):
        print "PostMedia called"
        """Called only when FEniCSbot wants to tweet solutions"""
        self.dummy_tweet(SOLUTION_TWEET)

    def PostUpdate(self, *args, **kwargs):
        print "PostUpdate called"
        """Called only when FEniCSbot wants to tweet errors"""
        self.dummy_tweet(ERROR_TWEET)

    def GetSearch(self, *args, **kwargs):
        """Called only when FEniCSbot wants to search for tweets"""
        print "GetSearch called"
        if len(self.mentions) > 0:
            mentions = self.mentions[0]
            self.mentions = self.mentions[1:]
            return mentions
        else:
            return []

def dummy_bot(list_of_tweet_text_lists):
    """
    Creates a dummy FEniCSbot which will receive batches of tweets
    with text given by list_of_tweet_text_lists, then exit when
    looking for the next batch of mentions
    """
    def loop_stopper(bot):
        return bot.api.is_empty()

    return FEniCSbot(DummyTwitterApi(list_of_tweet_text_lists),
                     sleep_time=SLEEP_TIME,
                     break_loop=loop_stopper)



def rebatch(l, l_sizes):
    """
    Helper method for running a test several times
    with different batch sizes.

    Resizes a plain list into a list of lists with the
    same elements, but with lengths given in l_sizes.

    Example:
    l = [1, 2, 3, 4, 5] becomes:
      --[[1, 2], [3, 4], [5]] with l_sizes = [2, 2, 1]
      --[[1, 2, 3, 4], [5]] with l_sizes = [4, 1]
      --[[1], [2], [3], [4], [5]] with l_sizes = [1, 1, 1, 1, 1]
      --[1, 2, 3, 4, 5] with l_sizes = [5]
    """
    # print l, l_sizes
    if len(l) != sum(l_sizes):
        raise Exception("User counting error")

    i = 0
    return_list = [[] for batch_size in l_sizes]
    for j in range(len(l_sizes)):
        batch_size = l_sizes[j]
        for _ in range(batch_size):
            return_list[j].append(l[i])
            i += 1
    # print return_list
    return return_list


@pytest.mark.parametrize(("l_ret", "l_sizes"), [
    ([[1, 2], [3, 4], [5]],  [2, 2, 1]),
    ([[1, 2, 3, 4], [5]],  [4, 1]),
    ([[1, 2, 3, 4, 5]],  [5]),
    ([[1], [2], [3], [4], [5]], [1, 1, 1, 1, 1])
])
def test_rebatch(l_sizes, l_ret):
    ## Has testing gone too far?

    l = range(1, 6)
    l_rebatched = rebatch(l, l_sizes)
    assert len(l_rebatched) == len(l_ret)
    for i in range(len(l_ret)):
        assert len(l_ret[i]) == len(l_rebatched[i])
        for j in range(len(l_ret[i])):
            assert l_ret[i][j] == l_rebatched[i][j]



def run_test_tweets(list_of_tweet_batches, list_of_success_statuses):
    """
    Takes as argument a list of tweet text batches, as well as a list of
    True/False values of the same 'shape' where True indicates that
    the tweet should result in success, while False indicates error
    """
    bot = dummy_bot(list_of_tweet_batches)
    bot.start()
    # try:
    #     bot.start()
    # except Exception as e:
    #     print e
    #     print bot.api.is_empty
    #     assert bot.api.is_empty


    # verify that all messages were "delivered" to fenicsbot


    tweet_no = 0
    # print list_of_tweet_batches
    # print bot.api.tweets
    # print list_of_tweet_batches
    for batch in list_of_success_statuses:
        for success_status in batch:
            if success_status:
                assert bot.api.tweets[tweet_no] == SOLUTION_TWEET
            else:
                assert bot.api.tweets[tweet_no] == ERROR_TWEET
            tweet_no += 1       # this could probably be prettier



@pytest.mark.parametrize("batch_sizes", [
    [2, 2, 1],
    [4, 1],
    [5],
    [1, 1, 1, 1, 1]
])
def test_good_tweets(batch_sizes):
    # Checks that these tweets are parsed without exception
    # even when given in batches of various sizes
    tweets = [
        "@fenicsbot Solve Poisson with f=1",
        "@fenicSbot Solve Poisson",
        "@FEniCSbot Solve Poisson with f=1 and domain=UnitSquare",
        "@feNicsBot Solve Stokes",
        "@feNicsBot Solve Stokes"
    ]
    statuses = [True]*5

    run_test_tweets(rebatch(tweets, batch_sizes),
                rebatch(statuses, batch_sizes))


@pytest.mark.parametrize("tweet", [
    "@fenisbot Solve Poisson with f=1",
    "Solve Poisson",
    "@fenicsbot Poisson with g=1 and D=2",
    "@fenicsbot Solve with f=1 and n=2",
    "@fenicsbot Solve",
    "@fenicsbot ",
    "@FEnCSbot Solve Poisson with f=1 and D=2",
])
def test_bad_tweet(tweet):
    batches = [[tweet]]
    statuses = [[False]]
    run_test_tweets(batches, statuses)


def test_single_good_tweet():
    batches = [["@fenicsbot Solve Poisson with domain=UnitSquare and f=cos(pi*x[0])*cos(pi*x[1])"]]
    statuses = [[True]]
    run_test_tweets(batches, statuses)


