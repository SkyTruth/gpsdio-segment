from __future__ import division, print_function, absolute_import
from collections import Counter
from itertools import chain
import logging
import math

logger = logging.getLogger(__file__)
logger.setLevel(logging.WARNING)

log = logger.warning


from .discrepancy import DiscrepancyCalculator

class Stitcher(DiscrepancyCalculator):
    """Stitch segments together into coherent tracks.
    """
    
    min_seed_size = 5 # minimum segment size to start a track
    min_seg_size = 3 # segments shorter than this are dropped
    max_average_knots = 25 # fastest speed we allow when connecting segments
    # min_dist = 10 * 0.1 # uncertainty due to type 27 messages
    penalty_hours = 12
    # hours_exp = 2.0
    buffer_hours = 1.0
    max_overlap_factor = 0.8
    duration_weight = 0.1
    overlap_weight = 1.0
    speed_0 = 12.5
    min_sig_match = -0.3
    penalty_tracks = 4 # for more than this number of tracks become more strict
                        # todo: possibly only apply when multiple tracks.
                        # todo: possibly factor size in somehow
                        # penalty_hours = 12
    base_hour_penalty = 1.5
    no_id_hour_penalty = 2.0 # be more strict for tracks with no id info joining them across long times
    speed_weight = 0.1
    
    def __init__(self, **kwargs):
        for k in kwargs:
            # TODO: when interface stable, fix keys as in core.py
            self._update(k, kwargs)
    
    @staticmethod
    def add_track_ids(msgs, tracks):
        # Use the seg_id of the first seg in the track as the track id.
        id_map = {}
        for track in tracks:
            track_id = track[0]['seg_id']
            for seg in track:
                id_map[seg['seg_id']] = track_id
        for msg in msgs:
            msg['track_id'] = id_map.get(msg['seg_id'], None)

    def _compute_signatures(self, segs):
        def get_sig(seg):
            return [
                {x['value'] : x['count'] for x in seg['transponders']},
                {x['value'] : x['count'] for x in seg['shipnames']},
                {x['value'] : x['count'] for x in seg['callsigns']},
                {x['value'] : x['count'] for x in seg['imos']},
            ]
        signatures = {}
        for seg in segs:
            sid = seg['seg_id']
            signatures[sid] = get_sig(seg)
        return signatures
    
    def uniquify_filter_and_sort(self, segs, min_seg_size=1):
        segs = [seg for seg in segs if seg['seg_id'] is not None 
                               and seg['message_count'] >= min_seg_size]
        segs.sort(key=lambda x: (x['first_msg_timestamp'], x['timestamp']))
        segsmap = {x['seg_id'] : x for x in segs}
        segs = sorted(segsmap.values(), key=lambda x: (x['first_msg_timestamp'], x['timestamp']))
        return segs
    
    def compute_signature_metric(self, signatures, seg1, seg2):
        sig1 = signatures[seg1['seg_id']][:2]
        sig2 = signatures[seg2['seg_id']][:2]

        match = []
        for a, b in zip(sig1, sig2):
            if len(a) and len(b):
                na = math.sqrt(sum([v**2 for v in a.values()]))
                nb = math.sqrt(sum([v**2 for v in b.values()]))
                if na and nb:
                    maxa = max(a.values()) / na
                    maxb = max(b.values()) / nb
                    cos = 0
                    ta = 0 
                    tb = 0
                    for k in set(a) & set(b):
                        va = a[k] / na
                        vb = b[k] / nb
                        cos += va * vb
                        ta += va ** 2
                        tb += vb ** 2
                    cos2 = 2 * cos ** 2 - 1
                    num_dims = len(set(a) | set(b))
                    # Specificity is an ad hoc measure of how much information the
                    # vector provides. From 0, when all components (identities) are
                    # equal to 1, when the vector has one identity (along an axis)
                    if num_dims == 1:
                        specificity = 1.0
                    else:
                        alpha = num_dims ** 0.5 / (num_dims ** 0.5 - 1)
                        beta = 1 / (num_dims ** 0.5 - 1)
                        specificity_a = alpha * maxa - beta
                        specificity_b = alpha * maxb - beta
                        specificity = specificity_a * specificity_b
                    # print('cos2, spec', cos2, specificity)
                    match.append(cos2 * specificity)
        log('signature 1: %s', sig1)
        log('signature 2: %s', sig2)
        log('match_vector: %s', match)
        if len(match) == 0:
            return self.min_sig_match, False
        elif len(match) == 1:
            sig_metric = match[0]
            return min(sig_metric, self.min_sig_match), False
        else:
            # The idea here is that we want to consider 
            #   (a) the worst match and
            #   (b) the most specific match
            # Minimizing x/wt minimizes a particular combination of
            # specificity and badness, then we multiply by weight to
            # get back the correct match value. There may be a cleaner
            # approach.
            return min(match), True

    
    def create_tracks(self, segs):
        segs = self.uniquify_filter_and_sort(segs, self.min_seg_size)
        signatures = self._compute_signatures(segs)
        # Build up tracks, joining to most reasonable segment (speed needed to join not crazy)
        tracks = []
        alive = True
        for seg in segs:
            # print('\n\n')
            best_track = None
            best_metric = 0
            for track in tracks:
                tgt = track[-1]
                sig_metric, had_match = self.compute_signature_metric(signatures, seg, tgt)
                log('sig_metric: %s, had_match: %s', sig_metric, had_match)

                seg_t0, seg_t1 = seg['first_msg_timestamp'], seg['last_msg_timestamp']
                tgt_t0, tgt_t1 = track[0]['first_msg_timestamp'], tgt['last_msg_timestamp']
                delta_hours = self.compute_ts_delta_hours(tgt_t1, seg_t0)
                log('delta_hours: %s', delta_hours)
                dt1 = self.compute_ts_delta_hours(seg_t0, seg_t1)
                dt2 = self.compute_ts_delta_hours(tgt_t0, tgt_t1)
                max_overlap_hours = min(dt1 * self.max_overlap_factor * sig_metric, 
                                        dt2 * self.max_overlap_factor * sig_metric)  

                log('max_overlap_hours: %s, dt1: %s, dt2: %s', 
                        max_overlap_hours, dt1, dt2)
                # print('Hours', delta_hours, max_overlap_hours, dt1, dt2, sig_metric)
                if delta_hours + max_overlap_hours <= 0:
                    continue 

                laxity = (1 if (len(tracks) < self.penalty_tracks) else 
                        math.sqrt(2) / math.hypot(1, len(tracks)/self.penalty_tracks))


                # print('sig_metric', sig_metric)
                
                hours_exp = 1.0 / self.base_hour_penalty if had_match else 1.0 / self.no_id_hour_penalty
        
                
                if laxity * sig_metric < self.min_sig_match:
                    # print('failing match', laxity, sig_metric, self.min_sig_match)
                    continue
                # print('succesful match', laxity, sig_metric, self.min_sig_match)

                msg0 = {'timestamp' : tgt['last_msg_timestamp'], 
                        'lat' : tgt['last_msg_lat'], 'lon' : tgt['last_msg_lon'],
                        'speed' : tgt['last_msg_speed'], 'course' : tgt['last_msg_course']}
                msg1 = {'timestamp' : seg['first_msg_timestamp'], 
                        'lat' : seg['first_msg_lat'], 'lon' : seg['first_msg_lon'],
                        'speed' : seg['first_msg_speed'], 'course' : seg['first_msg_course']}
                overlapped = tgt['last_msg_timestamp'] > seg['first_msg_timestamp']
                if overlapped:
                    # Segments overlap so flip the messages to keep time positive
                    msg0, msg1 = msg1, msg0


                hours = math.hypot(self.compute_msg_delta_hours(msg0, msg1), self.buffer_hours)
                effective_hours = (hours if (hours < self.penalty_hours) else 
                                   self.penalty_hours * (hours / self.penalty_hours) ** hours_exp)
                discrepancy = self.compute_discrepancy(msg0, msg1, effective_hours)

                speed = discrepancy / effective_hours
                log("discrepancy %s, effective_hours: %s", discrepancy, effective_hours)
                log('speed: %s, laxity: %s, max_average_knots: %s', speed, laxity, self.max_average_knots)
                if speed > self.max_average_knots * laxity:
                    log('failed speed test')
                    # print('failing speed match', speed, laxity, effective_hours)
                    continue

                speed_metric = math.exp(-(speed / self.speed_0) ** 2) / hours    

                duration_metric = math.log(dt2)
                overlap_metric = 1 if (delta_hours >= 0) else 1 - delta_hours / max_overlap_hours

                metric = (sig_metric + 
                          self.speed_weight * speed_metric + 
                          self.duration_weight * duration_metric +
                          self.overlap_weight * overlap_metric)
                # print(sig_metric, speed_metric, metric)
                if metric > best_metric:
                    best_metric = metric 
                    best_track = track
            if best_track is not None: 
                new_sigs = []
                new_counts = []
                for s1, s2 in zip(signatures[seg['seg_id']], 
                                          signatures[best_track[-1]['seg_id']]):
                    new_sig = {}
                    for k in set(s1.keys()) | set(s2.keys()):
                        new_sig[k] = s1.get(k, 0) + s2.get(k, 0) 
                    new_sigs.append(new_sig)
                signatures[seg['seg_id']] = new_sigs
                best_track.append(seg)
            elif seg['message_count'] >= self.min_seed_size:
                tracks.append([seg])
            # print()
            # print()
                
        return tracks